from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import pytest
from custom_components.azae.model import (SchemaError, Snapshot, parse_events, timestamp,
                                          pointer, presence, scheduled, validate_options)
UTC = timezone.utc
NOW = datetime(2026, 10, 9, 11, 0, tzinfo=UTC)

def row(**changes):
    return {"libelle": "ménage", "start": "2026-10-09 11:00:00", "end": "2026-10-09 14:00:00",
            "heure_pointage_debut": None, "heure_pointage_fin": None,
            "commentaire_annulation": "", **changes}

def snapshot(options, rows, now=NOW):
    return Snapshot(parse_events(rows, options), now, True)

def test_confirmed_schema_and_default_unknown(options):
    data = snapshot(options, [row()])
    assert data.events[0].start.hour == 9
    assert scheduled(data, NOW, options) is True
    assert presence(data, NOW, options) == (None, "no_confirmed_presence_source")

def test_half_open_empty_and_stale(options):
    data = snapshot(options, [row()])
    assert scheduled(data, data.events[0].end, options) is None  # cached data stale
    assert scheduled(snapshot(options, [row()], data.events[0].end), data.events[0].end, options) is False
    assert scheduled(snapshot(options, []), NOW, options) is False
    assert scheduled(Snapshot(None, NOW, False), NOW, options) is None
    assert scheduled(data, NOW + timedelta(seconds=600), options) is None

@pytest.mark.parametrize("value", [{"data": []}, None, [row(end="bad")], [row(end="2026-10-09 10:00:00")], [None]])
def test_schema_is_never_empty_planning(options, value):
    with pytest.raises(SchemaError):
        parse_events(value, options)

def test_pointer_no_guesses(options):
    assert pointer({"data": {"user": {"token": "synthetic-token"}}}, options["token_path"]) == "synthetic-token"
    assert pointer({"a/b": {"~": [7]}}, "/a~1b/~0/0") == 7
    with pytest.raises(SchemaError):
        pointer({"access_token": "x"}, options["token_path"])

@pytest.mark.parametrize("value", ["2026-03-29 02:30:00", "2026-10-25 02:30:00", "2026-10-09"])
def test_dst_ambiguous_nonexistent_and_date_only(value):
    with pytest.raises(SchemaError):
        timestamp(value, ZoneInfo("Europe/Paris"))

def test_dst_offsets_and_midnight(options):
    early = timestamp("2026-10-25T02:30:00+02:00", ZoneInfo("Europe/Paris"))
    late = timestamp("2026-10-25T02:30:00+01:00", ZoneInfo("Europe/Paris"))
    assert late - early == timedelta(hours=1)
    assert timestamp("2026-01-10 00:30:00", ZoneInfo("Europe/Paris")).day == 9
    events = parse_events([row(start="2026-10-09 23:00:00", end="2026-10-10 02:00:00")], options)
    assert events[0].end > events[0].start

def test_pointage(options):
    options["presence_mode"] = "pointage"
    assert presence(snapshot(options, [row()]), NOW, options) == (None, "no_recent_clock")
    active = row(heure_pointage_debut="2026-10-09 12:00:00")
    assert presence(snapshot(options, [active]), NOW, options) == (True, "open_clock")
    completed = row(heure_pointage_debut="2026-10-09 10:00:00", heure_pointage_fin="2026-10-09 12:00:00")
    assert presence(snapshot(options, [completed]), NOW, options) == (False, "closed_clock")
    assert presence(snapshot(options, [active, completed]), NOW, options) == (None, "conflicting_clocks")
    assert presence(snapshot(options, [row(heure_pointage_debut="2026-10-08 12:00:00")]), NOW, options)[1] == "expired_open_clock"
    assert presence(snapshot(options, [row(heure_pointage_debut="2026-10-10 12:00:00")]), NOW, options)[1] == "future_clock"
    assert presence(snapshot(options, [active]), NOW + timedelta(minutes=10), options)[1] == "stale_data"

def test_missing_clock_keys_are_not_null(options):
    options["presence_mode"] = "pointage"
    data = row()
    del data["heure_pointage_fin"]
    with pytest.raises(SchemaError):
        parse_events([data], options)

def test_bad_clock_order(options):
    options["presence_mode"] = "pointage"
    with pytest.raises(SchemaError):
        parse_events([row(heure_pointage_fin="2026-10-09 13:00:00")], options)

def test_filter_cancel_and_deduplicate(options):
    assert parse_events([row(commentaire_annulation="Annulée"), row(libelle="repassage")], options) == ()
    assert len(parse_events([row(), row()], options)) == 1

def test_options(options):
    validate_options(options)
    with pytest.raises(SchemaError):
        validate_options({**options, "timezone": "Never/Exists"})

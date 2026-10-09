"""Pure, strict adapter for the supplied response schema, with JSON pointers."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

UTC = timezone.utc

class SchemaError(Exception):
    """Response cannot be interpreted safely (never includes raw data)."""

def pointer(data, path):
    """RFC 6901 JSON pointer, empty string selects root."""
    if path == "":
        return data
    if not isinstance(path, str) or not path.startswith("/"):
        raise SchemaError("invalid_pointer")
    try:
        for part in path[1:].split("/"):
            part = part.replace("~1", "/").replace("~0", "~")
            data = data[int(part)] if isinstance(data, list) and part.isdecimal() else data[part]
        return data
    except (KeyError, IndexError, TypeError, ValueError):
        raise SchemaError("missing_field") from None

def timestamp(value, zone):
    """ISO datetime or observed SQL datetime; reject ambiguous local times."""
    if not isinstance(value, str) or len(value) < 16:
        raise SchemaError("invalid_datetime")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise SchemaError("invalid_datetime") from None
    if result.tzinfo is None:
        candidates = set()
        for fold in (0, 1):
            aware = result.replace(tzinfo=zone, fold=fold)
            utc = aware.astimezone(UTC)
            if utc.astimezone(zone).replace(tzinfo=None) == result:
                candidates.add(utc)
        if len(candidates) != 1:
            raise SchemaError("ambiguous_or_nonexistent_datetime")
        return candidates.pop()
    return result.astimezone(UTC)

@dataclass(frozen=True)
class Intervention:
    start: datetime
    end: datetime
    clock_in: datetime | None
    clock_out: datetime | None

@dataclass(frozen=True)
class Snapshot:
    events: tuple[Intervention, ...] | None
    fetched_at: datetime
    schema_ok: bool

def validate_options(options):
    try:
        ZoneInfo(options["timezone"])
    except (ZoneInfoNotFoundError, ValueError, TypeError):
        raise SchemaError("invalid_timezone") from None
    for key in ("token_path", "events_path", "start_path", "end_path", "clock_in_path", "clock_out_path"):
        path = options[key]
        if not isinstance(path, str) or (path and not path.startswith("/")):
            raise SchemaError("invalid_pointer")
    if options["presence_mode"] not in ("unknown", "pointage"):
        raise SchemaError("invalid_mode")
    if not 60 <= options["poll_seconds"] <= 3600 or not 1 <= options["evidence_hours"] <= 24:
        raise SchemaError("invalid_interval")

def parse_events(payload, options):
    """All-or-nothing: malformed data must never become an empty planning."""
    rows = pointer(payload, options["events_path"])
    if not isinstance(rows, list):
        raise SchemaError("expected_list")
    zone = ZoneInfo(options["timezone"])
    events = []
    for row in rows:
        if not isinstance(row, dict):
            raise SchemaError("expected_object")
        label = row.get("libelle")
        if options["label_filter"]:
            if not isinstance(label, str):
                raise SchemaError("missing_label")
            if options["label_filter"].casefold() not in label.casefold():
                continue
        # This field is a cancellation comment, not a presence indication.
        cancellation = row.get("commentaire_annulation", "")
        if not isinstance(cancellation, (str, type(None))):
            raise SchemaError("invalid_cancellation")
        if cancellation and cancellation.strip():
            continue
        start = timestamp(pointer(row, options["start_path"]), zone)
        end = timestamp(pointer(row, options["end_path"]), zone)
        if end <= start:
            raise SchemaError("invalid_interval")
        clock_in = clock_out = None
        if options["presence_mode"] == "pointage":
            # Missing keys differ from explicit null: fail closed on schema drift.
            value_in = pointer(row, options["clock_in_path"])
            value_out = pointer(row, options["clock_out_path"])
            clock_in = None if value_in is None else timestamp(value_in, zone)
            clock_out = None if value_out is None else timestamp(value_out, zone)
            if clock_out is not None and (clock_in is None or clock_out < clock_in):
                raise SchemaError("invalid_clock_order")
        events.append(Intervention(start, end, clock_in, clock_out))
    return tuple(sorted(set(events), key=lambda item: (item.start, item.end)))

def fresh(snapshot, now, options):
    return snapshot is not None and timedelta(0) <= now - snapshot.fetched_at < timedelta(seconds=options["poll_seconds"] * 2)

def scheduled(snapshot, now, options):
    if not fresh(snapshot, now, options) or snapshot.events is None:
        return None
    return any(item.start <= now < item.end for item in snapshot.events)

def presence(snapshot, now, options):
    """Clock declarations, never a conclusion from scheduled intervals."""
    if options["presence_mode"] != "pointage":
        return None, "no_confirmed_presence_source"
    if not fresh(snapshot, now, options):
        return None, "stale_data"
    if snapshot.events is None:
        return None, "unsupported_response"
    horizon = timedelta(hours=options["evidence_hours"])
    recent = []
    for item in snapshot.events:
        if item.clock_in is None:
            continue
        # A future declaration or an old unclosed shift is inconsistent, not absent.
        if item.clock_in > now or (item.clock_out is not None and item.clock_out > now):
            return None, "future_clock"
        if item.clock_out is None:
            if now - item.clock_in >= horizon:
                return None, "expired_open_clock"
            recent.append((item.clock_in, True))
        elif now - item.clock_out < horizon:
            recent.append((item.clock_out, False))
    if not recent:
        return None, "no_recent_clock"
    states = {state for _, state in recent}
    # Overlapping open/closed records may involve multiple workers; stay cautious.
    if len(states) > 1:
        return None, "conflicting_clocks"
    state = recent[0][1]
    return state, "open_clock" if state else "closed_clock"

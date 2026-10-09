from datetime import datetime, timedelta, timezone
from unittest.mock import patch, AsyncMock
import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry
from custom_components.azae.api import AuthError, ApiError, RateLimitError
from custom_components.azae.coordinator import AzaeCoordinator
from custom_components.azae.diagnostics import async_get_config_entry_diagnostics
from custom_components.azae.calendar import AzaeCalendar
from custom_components.azae.const import DOMAIN
from custom_components.azae.model import Snapshot
from homeassistant.helpers.update_coordinator import UpdateFailed

NOW = datetime(2026, 10, 9, 11, tzinfo=timezone.utc)

def row():
    return {"libelle": "ménage", "start": "2026-10-09 12:00:00", "end": "2026-10-09 14:00:00",
            "heure_pointage_debut": "2026-10-09 12:00:00", "heure_pointage_fin": None}

async def test_setup_unknown_schema_network_recovery_and_unload(hass, account, options, mock_api, freezer):
    freezer.move_to(NOW)
    entry = MockConfigEntry(domain=DOMAIN, data=account, options=options)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    registry = er.async_get(hass)
    entities = {suffix: registry.async_get_entity_id(platform, DOMAIN, f"{entry.entry_id}_{suffix}") for suffix, platform in [("presence", "binary_sensor"), ("scheduled", "binary_sensor"), ("calendar", "calendar")]}
    assert hass.states.get(entities["presence"]).state == "unknown"
    assert hass.states.get(entities["scheduled"]).state == "off"
    mock_api[1].return_value = {"unexpected": []}
    await entry.runtime_data.async_refresh()
    assert hass.states.get(entities["scheduled"]).state == "unknown"
    assert hass.states.get(entities["calendar"]).state == "unavailable"
    mock_api[1].side_effect = ApiError()
    await entry.runtime_data.async_refresh()
    assert hass.states.get(entities["presence"]).state == "unavailable"
    mock_api[1].side_effect = None
    mock_api[1].return_value = [row()]
    await entry.runtime_data.async_refresh()
    assert hass.states.get(entities["scheduled"]).state == "on"
    assert hass.states.get(entities["presence"]).state == "unknown"
    diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    assert "password" not in repr(diagnostics) and "email" not in repr(diagnostics)
    assert diagnostics["event_count"] == 1
    coordinator = entry.runtime_data
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert hass.states.get(entities["presence"]).state == "unavailable"
    assert not coordinator._listeners

async def test_calendar_range_boundaries_and_errors(hass, account, options, mock_api, freezer):
    freezer.move_to(NOW)
    entry = MockConfigEntry(domain=DOMAIN, data=account, options=options)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    calendar = AzaeCalendar(entry.runtime_data)
    mock_api[1].return_value = [row()]
    result = await calendar.async_get_events(hass, NOW, NOW + timedelta(days=60))
    assert len(result) == 1
    assert result[0].summary == "Intervention Azaé (planning)"
    assert await calendar.async_get_events(hass, NOW + timedelta(hours=1), NOW + timedelta(hours=2)) == []
    with pytest.raises(HomeAssistantError):
        await calendar.async_get_events(hass, NOW, NOW + timedelta(days=400))
    mock_api[1].return_value = {"error": "private-body"}
    with pytest.raises(HomeAssistantError):
        await calendar.async_get_events(hass, NOW, NOW + timedelta(days=1))
    await hass.config_entries.async_unload(entry.entry_id)

@pytest.mark.parametrize("error,exception", [(AuthError(), ConfigEntryAuthFailed), (ApiError(), UpdateFailed), (RateLimitError(900), UpdateFailed)])
async def test_coordinator_error_mapping(hass, account, options, error, exception):
    entry = MockConfigEntry(domain=DOMAIN, data=account, options=options)
    entry.add_to_hass(hass)
    api = AsyncMock()
    api.hours.side_effect = error
    coordinator = AzaeCoordinator(hass, entry, api, options)
    with pytest.raises(exception):
        await coordinator._async_update_data()

async def test_pointage_staleness_and_schema_drift(hass, account, options, mock_api, freezer):
    options["presence_mode"] = "pointage"
    freezer.move_to(NOW)
    mock_api[1].return_value = [row()]
    entry = MockConfigEntry(domain=DOMAIN, data=account, options=options)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    entity_id = er.async_get(hass).async_get_entity_id("binary_sensor", DOMAIN, f"{entry.entry_id}_presence")
    assert hass.states.get(entity_id).state == "on"
    freezer.move_to(NOW + timedelta(seconds=601))
    data = entry.runtime_data.data
    entry.runtime_data.async_set_updated_data(Snapshot(data.events, NOW, True))
    assert hass.states.get(entity_id).state == "unknown"
    mock_api[1].return_value = [{"libelle": "ménage", "start": "invalid"}]
    await entry.runtime_data.async_refresh()
    assert hass.states.get(entity_id).state == "unknown"
    await hass.config_entries.async_unload(entry.entry_id)

async def test_calendar_auth_starts_reauth(hass, account, options, mock_api, freezer):
    freezer.move_to(NOW)
    entry = MockConfigEntry(domain=DOMAIN, data=account, options=options)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    mock_api[1].side_effect = AuthError()
    with patch.object(type(entry), "async_start_reauth") as reauth:
        with pytest.raises(HomeAssistantError):
            await entry.runtime_data.calendar_events(NOW, NOW + timedelta(days=1))
        reauth.assert_called_once_with(hass)
    await hass.config_entries.async_unload(entry.entry_id)

async def test_local_timer_expires_pointage_and_planning_without_api(hass, account, options, mock_api, freezer):
    from pytest_homeassistant_custom_component.common import async_fire_time_changed
    options["presence_mode"] = "pointage"
    freezer.move_to(NOW)
    data = row()
    data["heure_pointage_debut"] = "2026-10-09 05:00:10"
    data["end"] = "2026-10-09 13:00:10"
    mock_api[1].return_value = [data]
    entry = MockConfigEntry(domain=DOMAIN, data=account, options=options)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    registry = er.async_get(hass)
    presence_id = registry.async_get_entity_id("binary_sensor", DOMAIN, f"{entry.entry_id}_presence")
    scheduled_id = registry.async_get_entity_id("binary_sensor", DOMAIN, f"{entry.entry_id}_scheduled")
    assert hass.states.get(presence_id).state == "on"
    assert hass.states.get(scheduled_id).state == "on"
    calls = mock_api[1].call_count
    later = NOW + timedelta(seconds=31)
    freezer.move_to(later)
    async_fire_time_changed(hass, later)
    await hass.async_block_till_done()
    assert hass.states.get(presence_id).state == "unknown"
    assert hass.states.get(presence_id).attributes["reason"] == "expired_open_clock"
    assert hass.states.get(scheduled_id).state == "off"
    assert mock_api[1].call_count == calls
    await hass.config_entries.async_unload(entry.entry_id)

"""Diagnostics intentionally contain no API payload or config-entry data."""
async def async_get_config_entry_diagnostics(hass, entry):
    coordinator = entry.runtime_data
    data = coordinator.data
    return {"last_update_success": coordinator.last_update_success,
            "schema_ok": data.schema_ok if data else None,
            "event_count": len(data.events) if data and data.events is not None else None,
            "presence_mode": coordinator.options["presence_mode"],
            "timezone": coordinator.options["timezone"],
            "poll_seconds": coordinator.options["poll_seconds"]}

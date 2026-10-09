"""Azaé / A2micile custom integration."""
from homeassistant.const import Platform
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .api import AzaeApi
from .const import DEFAULTS
from .coordinator import AzaeCoordinator

PLATFORMS = [Platform.BINARY_SENSOR, Platform.CALENDAR]

async def async_setup_entry(hass, entry):
    options = {**DEFAULTS, **entry.options}
    api = AzaeApi(async_get_clientsession(hass), entry.data["email"], entry.data["password"],
                  entry.data["code_agence"], entry.data["matricule"], options["token_path"])
    coordinator = AzaeCoordinator(hass, entry, api, options)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_reload))
    return True

async def _reload(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass, entry):
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

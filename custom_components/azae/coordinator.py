"""Single shared poll, conservative schema handling and on-demand calendar fetch."""
from datetime import timedelta
import logging
from zoneinfo import ZoneInfo
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from .api import ApiError, AuthError, RateLimitError
from .const import DOMAIN
from .model import SchemaError, Snapshot, parse_events

_LOGGER = logging.getLogger(__name__)

class AzaeCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry, api, options):
        super().__init__(hass, _LOGGER, name=DOMAIN, config_entry=entry,
                         update_interval=timedelta(seconds=options["poll_seconds"]))
        self.api = api
        self.options = options
        self.zone = ZoneInfo(options["timezone"])

    async def _async_update_data(self):
        today = dt_util.utcnow().astimezone(self.zone).date()
        try:
            payload = await self.api.hours(today - timedelta(days=2), today + timedelta(days=31))
        except AuthError:
            raise ConfigEntryAuthFailed("Authentication rejected") from None
        except RateLimitError as err:
            raise UpdateFailed("Rate limited", retry_after=err.retry_after) from None
        except SchemaError:
            raise UpdateFailed("Login response schema unsupported; check token path") from None
        except ApiError:
            raise UpdateFailed("API request failed") from None
        now = dt_util.utcnow()
        try:
            return Snapshot(parse_events(payload, self.options), now, True)
        except SchemaError:
            # Unknown is distinct from a network failure and from an empty calendar.
            return Snapshot(None, now, False)

    async def calendar_events(self, start, end):
        if end <= start or end - start > timedelta(days=366):
            raise HomeAssistantError("Calendar range must be positive and at most 366 days")
        try:
            payload = await self.api.hours(start.astimezone(self.zone).date(), end.astimezone(self.zone).date())
            events = parse_events(payload, self.options)
        except AuthError:
            self.config_entry.async_start_reauth(self.hass)
            raise HomeAssistantError("Authentication rejected") from None
        except (ApiError, SchemaError):
            raise HomeAssistantError("Calendar data unavailable or schema unsupported") from None
        return [item for item in events if item.end > start and item.start < end]

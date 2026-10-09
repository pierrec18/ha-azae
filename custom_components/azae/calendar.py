"""Read-only intervention calendar, including arbitrary requested ranges."""
from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.util import dt as dt_util
from .entity import AzaeEntity
from .model import fresh

async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([AzaeCalendar(entry.runtime_data)])

class AzaeCalendar(AzaeEntity, CalendarEntity):
    _attr_icon = "mdi:calendar"

    def __init__(self, coordinator):
        super().__init__(coordinator, "calendar", "Azaé Interventions")

    @property
    def available(self):
        data = self.coordinator.data
        return (super().available and fresh(data, dt_util.utcnow(), self.coordinator.options)
                and data.events is not None)

    @staticmethod
    def _event(item):
        return CalendarEvent(start=item.start, end=item.end, summary="Intervention Azaé (planning)")

    @property
    def event(self):
        data = self.coordinator.data
        if data is None or data.events is None:
            return None
        now = dt_util.utcnow()
        for item in data.events:
            if item.end > now:
                return self._event(item)
        return None

    async def async_get_events(self, hass, start_date, end_date):
        return [self._event(item) for item in await self.coordinator.calendar_events(start_date, end_date)]

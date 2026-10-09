"""Separate clock declaration from scheduled activity."""
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.util import dt as dt_util
from .entity import AzaeEntity
from .model import presence, scheduled

async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([AzaePresence(entry.runtime_data), AzaeScheduled(entry.runtime_data)])

class AzaePresence(AzaeEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.OCCUPANCY
    _attr_icon = "mdi:account-clock"

    def __init__(self, coordinator):
        super().__init__(coordinator, "presence", "Azaé Présence déclarée")

    @property
    def is_on(self):
        return presence(self.coordinator.data, dt_util.utcnow(), self.coordinator.options)[0]

    @property
    def extra_state_attributes(self):
        return {"source": self.coordinator.options["presence_mode"],
                "reason": presence(self.coordinator.data, dt_util.utcnow(), self.coordinator.options)[1],
                "physical_presence_verified": False}

class AzaeScheduled(AzaeEntity, BinarySensorEntity):
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator):
        super().__init__(coordinator, "scheduled", "Azaé Intervention planifiée")

    @property
    def is_on(self):
        return scheduled(self.coordinator.data, dt_util.utcnow(), self.coordinator.options)

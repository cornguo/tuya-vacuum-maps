"""Sensor for the room the vacuum is in."""

from typing import Any

from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import VacuumMapRuntime
from .entity import VacuumMapEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add the current room sensor."""
    async_add_entities([CurrentRoomSensor(config_entry.runtime_data)])


class CurrentRoomSensor(VacuumMapEntity, SensorEntity):
    """The room the vacuum is in, from the end of its path on the map.

    It's as current as the map: the vacuum uploads its path while cleaning.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "current_room"
    _attr_icon = "mdi:map-marker"

    def __init__(self, runtime: VacuumMapRuntime) -> None:
        """Initialize the sensor."""
        super().__init__(runtime, SENSOR_DOMAIN, "current_room")

    @property
    def native_value(self) -> str | None:
        """Return the room's name, or None when it isn't in a room."""
        data = self.coordinator.data
        return data.rooms.get(data.current_room)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the room's id."""
        return {"room_id": self.coordinator.data.current_room}

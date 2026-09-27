"""Button that starts cleaning the selected rooms."""

from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN, ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import VacuumMapRuntime
from .entity import VacuumMapEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add the clean button."""
    async_add_entities([CleanRoomsButton(config_entry.runtime_data)])


class CleanRoomsButton(VacuumMapEntity, ButtonEntity):
    """Clean the rooms selected with the room switches."""

    _attr_has_entity_name = True
    _attr_name = "Clean selected rooms"
    _attr_icon = "mdi:robot-vacuum"

    def __init__(self, runtime: VacuumMapRuntime) -> None:
        """Initialize the button."""
        super().__init__(runtime, BUTTON_DOMAIN, "clean_rooms")

    async def async_press(self) -> None:
        """Start cleaning the selected rooms, in the order they were selected."""
        rooms = self.coordinator.data.rooms
        room_ids = [
            room_id for room_id in self._runtime.selected_rooms if room_id in rooms
        ]
        if not room_ids:
            raise HomeAssistantError("Select at least one room to clean")
        await self.coordinator.async_clean_rooms(room_ids, self._runtime.clean_passes)

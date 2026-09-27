"""Number of passes when cleaning rooms."""

from homeassistant.components.number import (
    DOMAIN as NUMBER_DOMAIN,
    NumberMode,
    RestoreNumber,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import VacuumMapRuntime
from .entity import VacuumMapEntity
from .room_command import MAX_CLEAN_PASSES, MIN_CLEAN_PASSES


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add the cleaning passes slider."""
    async_add_entities([CleanPassesNumber(config_entry.runtime_data)])


class CleanPassesNumber(VacuumMapEntity, RestoreNumber):
    """How many times each selected room is cleaned."""

    _attr_has_entity_name = True
    _attr_name = "Clean passes"
    _attr_icon = "mdi:repeat"
    _attr_mode = NumberMode.SLIDER
    _attr_native_min_value = MIN_CLEAN_PASSES
    _attr_native_max_value = MAX_CLEAN_PASSES
    _attr_native_step = 1

    def __init__(self, runtime: VacuumMapRuntime) -> None:
        """Initialize the slider."""
        super().__init__(runtime, NUMBER_DOMAIN, "clean_passes")

    @property
    def native_value(self) -> int:
        """Return the number of passes."""
        return self._runtime.clean_passes

    async def async_added_to_hass(self) -> None:
        """Restore the number of passes."""
        await super().async_added_to_hass()
        last_number = await self.async_get_last_number_data()
        if last_number and last_number.native_value is not None:
            self._runtime.clean_passes = int(last_number.native_value)

    async def async_set_native_value(self, value: float) -> None:
        """Set the number of passes."""
        self._runtime.clean_passes = int(value)
        self.async_write_ha_state()

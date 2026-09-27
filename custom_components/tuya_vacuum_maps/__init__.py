"""Tuya Vacuum Maps integration."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from . import map_type_filter, path_style, room_parser
from .coordinator import VacuumMapCoordinator, VacuumMapRuntime
from .entity import entity_id_prefix, map_device

PLATFORMS = [Platform.BUTTON, Platform.CAMERA, Platform.NUMBER, Platform.SWITCH]

_LOGGER = logging.getLogger(__name__)
logging.getLogger("tuya_vacuum").setLevel(logging.DEBUG)
map_type_filter.apply()

# Patch tuya-vacuum before the config flow or camera parses any map
room_parser.apply()
path_style.apply()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tuya Vacuum Maps from a config entry."""

    coordinator = VacuumMapCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    device_info, tuya_local_object_id = map_device(hass, entry)
    entry.runtime_data = VacuumMapRuntime(
        coordinator=coordinator,
        device_info=device_info,
        tuya_local_object_id=tuya_local_object_id,
        entity_id_prefix=entity_id_prefix(entry, tuya_local_object_id),
    )

    # Create each HA object for each plaform the device requires.
    # It's done by calling the `async_setup_entry` function in each platform module.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    # This is called when an entry/configured device is to be removed.
    # The class needs to unload itself and remove callbacks.
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

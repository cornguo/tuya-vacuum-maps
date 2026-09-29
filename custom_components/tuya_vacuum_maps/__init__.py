"""Tuya Vacuum Maps integration."""

import hashlib
import logging
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType

from . import area_cleaning, map_type_filter, path_style, room_parser
from .card_resource import async_register_card, async_unregister_card
from .const import CONF_AREA_CLEANING, DOMAIN
from .coordinator import VacuumMapCoordinator, VacuumMapRuntime
from .entity import entity_id_prefix, map_device

PLATFORMS = [
    Platform.BUTTON,
    Platform.CAMERA,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

# Dashboard card for the room switches, passes slider and clean button
CARD_FILE = Path(__file__).parent / "frontend" / "tuya-vacuum-maps-rooms-card.js"
CARD_URL = f"/{DOMAIN}/tuya-vacuum-maps-rooms-card.js"

_LOGGER = logging.getLogger(__name__)
logging.getLogger("tuya_vacuum").setLevel(logging.DEBUG)
map_type_filter.apply()

# Patch tuya-vacuum before the config flow or camera parses any map
room_parser.apply()
path_style.apply()


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Serve the dashboard card and load it on dashboards."""
    card_hash = await hass.async_add_executor_job(
        lambda: hashlib.sha256(CARD_FILE.read_bytes()).hexdigest()[:8]
    )
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(CARD_FILE), True)]
    )
    # The hash makes browsers load a changed card instead of a cached one
    await async_register_card(hass, CARD_URL, card_hash)
    return True


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

    # Area cleaning on the Tuya Local vacuum, with the map's rooms
    if entry.options.get(CONF_AREA_CLEANING, False):
        await area_cleaning.async_link(hass, entry.entry_id, entry.runtime_data)
        entry.async_on_unload(
            lambda: area_cleaning.unlink(hass, entry.entry_id, entry.runtime_data)
        )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    # This is called when an entry/configured device is to be removed.
    # The class needs to unload itself and remove callbacks.
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await hass.async_add_executor_job(entry.runtime_data.coordinator.close)
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove the rooms card resource with the last entry."""
    if not any(
        other.entry_id != entry.entry_id
        for other in hass.config_entries.async_entries(DOMAIN)
    ):
        await async_unregister_card(hass, CARD_URL)

"""Fetch the vacuum map for all of an entry's entities."""

from dataclasses import dataclass, field
from datetime import timedelta
import io
import logging
from pathlib import Path

import tuya_vacuum

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .cloud_commands import send_commands
from .const import DOMAIN
from .room_command import MIN_CLEAN_PASSES, room_clean_commands
from .room_labels import draw_room_labels, room_label_positions, rooms_in_map_order

UPDATE_INTERVAL = timedelta(seconds=10)

# Rooms whose labels are within this fraction of the map height of each other
# count as one row when ordering rooms as they appear on the map
ROW_HEIGHT_FRACTION = 1 / 15

_LOGGER = logging.getLogger(__name__)


@dataclass
class MapData:
    """The latest map of the vacuum."""

    image: bytes
    # Room names by room id
    rooms: dict[int, str]
    # Room ids as they appear on the map, top left to bottom right
    map_order: list[int]


class VacuumMapCoordinator(DataUpdateCoordinator[MapData]):
    """Fetch and render the realtime map of a vacuum."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=entry.title,
            update_interval=UPDATE_INTERVAL,
        )
        self._font_cache_dir = Path(hass.config.path(".cache", DOMAIN))

    async def _async_update_data(self) -> MapData:
        """Fetch the map, running the blocking calls in the executor."""
        try:
            return await self.hass.async_add_executor_job(self._fetch_map)
        except Exception as err:  # pylint: disable=broad-except
            raise UpdateFailed(f"Could not fetch the vacuum map: {err}") from err

    def _fetch_map(self) -> MapData:
        """Fetch the realtime map and render it as PNG bytes."""
        data = self.config_entry.data
        vacuum = tuya_vacuum.TuyaVacuum(
            data["server"], data["client_id"], data["client_secret"], data["device_id"]
        )
        vacuum_map = vacuum.fetch_realtime_map()

        image = vacuum_map.to_image()
        rooms = {}
        map_order = []
        # Only version 1 layouts carry room info
        if vacuum_map.layout.version == 1:
            draw_room_labels(image, vacuum_map.layout, self._font_cache_dir)
            rooms = {
                room.id: room.name.rstrip("\0") or f"Room {room.id}"
                for room in vacuum_map.layout.rooms
            }
            map_order = rooms_in_map_order(
                room_label_positions(vacuum_map.layout),
                vacuum_map.layout.height * ROW_HEIGHT_FRACTION,
            )

        image_bytes = io.BytesIO()
        image.save(image_bytes, format="PNG")
        return MapData(image=image_bytes.getvalue(), rooms=rooms, map_order=map_order)

    async def async_clean_rooms(self, room_ids: list[int], clean_passes: int) -> None:
        """Make the vacuum clean the given rooms, in the given order."""
        data = self.config_entry.data
        try:
            await self.hass.async_add_executor_job(
                send_commands,
                data["server"],
                data["client_id"],
                data["client_secret"],
                data["device_id"],
                room_clean_commands(room_ids, clean_passes),
            )
        except Exception as err:  # pylint: disable=broad-except
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="clean_failed",
                translation_placeholders={"error": str(err)},
            ) from err


@dataclass
class VacuumMapRuntime:
    """What an entry's entities share."""

    coordinator: VacuumMapCoordinator
    device_info: DeviceInfo
    # Object id of the vacuum's Tuya Local vacuum entity, e.g. "robot"
    tuya_local_object_id: str | None
    # Object id the entity ids start with, e.g. "robot" for switch.robot_room_0
    entity_id_prefix: str
    # Rooms to clean, in the order they were selected
    selected_rooms: list[int] = field(default_factory=list)
    # Place of each room in the order before a restart, by room id
    restored_order: dict[int, float] = field(default_factory=dict)
    clean_passes: int = MIN_CLEAN_PASSES

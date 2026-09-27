"""Fetch the vacuum map for all of an entry's entities."""

from dataclasses import dataclass, field
import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .cloud import TuyaCloud
from .const import DOMAIN
from .map_render import MapData, MapRenderer
from .polling import ACTIVE_INTERVAL, update_interval
from .room_command import MIN_CLEAN_PASSES, room_clean_commands
from .virtual_areas import VirtualAreas, update_virtual_areas

# Map files the realtime map API returns that are drawn: 0 is the layout and
# 1 the path (2 is the incremental path and 3 the planning path)
LAYOUT_MAP_TYPE = 0
PATH_MAP_TYPE = 1

_LOGGER = logging.getLogger(__name__)


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
            update_interval=ACTIVE_INTERVAL,
            # Unchanged maps don't update the entities
            always_update=False,
        )
        self._renderer = MapRenderer(Path(hass.config.path(".cache", DOMAIN)))
        # Created in the executor, as creating its HTTP client loads certificates
        self._cloud: TuyaCloud | None = None
        # Last reported virtual walls and zones
        self._virtual_areas = VirtualAreas()
        self._status_failed = False
        # Value of the vacuum's `status` data point, e.g. "cleaning"
        self._vacuum_status: str | None = None

    async def _async_update_data(self) -> MapData:
        """Fetch the map, running the blocking calls in the executor."""
        try:
            data = await self.hass.async_add_executor_job(self._fetch_map)
        except Exception as err:  # pylint: disable=broad-except
            raise UpdateFailed(f"Could not fetch the vacuum map: {err}") from err
        # Fetch less often while the vacuum is idle, e.g. docked
        self.update_interval = update_interval(self._vacuum_status)
        return data

    def _get_cloud(self) -> TuyaCloud:
        """Return the Tuya Cloud client. Call it in the executor."""
        if self._cloud is None:
            data = self.config_entry.data
            self._cloud = TuyaCloud(
                data["server"], data["client_id"], data["client_secret"]
            )
        return self._cloud

    def close(self) -> None:
        """Close the Tuya Cloud client's connection. Call it in the executor."""
        if self._cloud is not None:
            self._cloud.close()

    def _fetch_map(self) -> MapData:
        """Fetch the realtime map and render it as PNG bytes."""
        cloud = self._get_cloud()
        device_id = self.config_entry.data["device_id"]
        files = {
            item["map_type"]: cloud.download(item["map_url"]).hex()
            for item in cloud.get(f"/v1.0/users/sweepers/file/{device_id}/realtime-map")
            if item["map_type"] in (LAYOUT_MAP_TYPE, PATH_MAP_TYPE)
        }
        self._read_status(cloud, device_id)
        return self._renderer.render(
            files.get(LAYOUT_MAP_TYPE), files.get(PATH_MAP_TYPE), self._virtual_areas
        )

    def _read_status(self, cloud: TuyaCloud, device_id: str) -> None:
        """Read what the vacuum is doing, and its virtual walls and zones.

        Failing to read them leaves the walls and zones off the map and polls
        often, logged once.
        """
        try:
            result = cloud.get(f"/v1.0/devices/{device_id}/status")
            status = {item["code"]: item["value"] for item in result}
            update_virtual_areas(self._virtual_areas, status.get("command_trans", ""))
            self._vacuum_status = status.get("status")
        except Exception as err:  # pylint: disable=broad-except
            self._vacuum_status = None
            if not self._status_failed:
                _LOGGER.warning("Could not read the vacuum's status: %s", err)
            self._status_failed = True
        else:
            self._status_failed = False

    async def async_clean_rooms(self, room_ids: list[int], clean_passes: int) -> None:
        """Make the vacuum clean the given rooms, in the given order."""
        device_id = self.config_entry.data["device_id"]
        commands = room_clean_commands(room_ids, clean_passes)
        try:
            await self.hass.async_add_executor_job(
                lambda: self._get_cloud().post(
                    f"/v1.0/devices/{device_id}/commands", {"commands": commands}
                )
            )
        except Exception as err:  # pylint: disable=broad-except
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="clean_failed",
                translation_placeholders={"error": str(err)},
            ) from err
        # Follow the vacuum as it starts, instead of waiting for an idle poll
        self.update_interval = ACTIVE_INTERVAL
        await self.async_request_refresh()


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

"""Add area cleaning to Tuya Local's vacuum entity.

Home Assistant's area cleaning ("Map vacuum segments to areas" and
vacuum.clean_area) works on the vacuum entity that reports the rooms, and an
integration can't add it to another's entity. So Tuya Local's vacuum class is
patched: for a vacuum set up here, it reports the map's rooms as segments and
cleans them with the room clean command. Other Tuya Local vacuums are left as
they are.

It relies on Tuya Local's internals (TuyaLocalVacuum in
custom_components.tuya_local.vacuum, its supported_features property and its
_device), so the patch is skipped, with a warning, if they change.
"""

from collections.abc import Callable, Iterable, Mapping
import importlib
import logging
import sys
from typing import Any

from .const import TUYA_LOCAL_DOMAIN

TUYA_LOCAL_VACUUM_MODULE = "custom_components.tuya_local.vacuum"
TUYA_LOCAL_VACUUM_CLASS = "TuyaLocalVacuum"
# Set on the class once it's patched
_PATCHED = "_tuya_vacuum_maps_area_cleaning"

_LOGGER = logging.getLogger(__name__)


def rooms_as_segments(
    rooms: Mapping[int, str], map_order: Iterable[int]
) -> list[tuple[str, str]]:
    """Return the (id, name) of each room, as they appear on the map."""
    ordered = [room_id for room_id in map_order if room_id in rooms]
    ordered += sorted(rooms.keys() - set(ordered))
    return [(str(room_id), rooms[room_id]) for room_id in ordered]


def room_ids_from_segments(
    segment_ids: Iterable[str], rooms: Mapping[int, str]
) -> list[int]:
    """Return the ids of the rooms still on the map, in the segments' order."""
    room_ids = []
    for segment_id in segment_ids:
        try:
            room_id = int(segment_id)
        except ValueError:
            continue
        if room_id in rooms and room_id not in room_ids:
            room_ids.append(room_id)
    return room_ids


class AreaCleaningLinks:
    """The entries whose vacuums get area cleaning, found by their device."""

    def __init__(self) -> None:
        """Initialize with no entries."""
        # VacuumMapRuntime by entry id
        self._runtimes: dict[str, Any] = {}

    def add(self, entry_id: str, runtime: Any) -> None:
        """Give the entry's vacuum area cleaning."""
        self._runtimes[entry_id] = runtime

    def remove(self, entry_id: str) -> None:
        """Take area cleaning away from the entry's vacuum."""
        self._runtimes.pop(entry_id, None)

    def runtime_for(self, entity: Any) -> Any:
        """Return the runtime of the entry with a Tuya Local vacuum's device."""
        device = getattr(entity, "_device", None)
        if device is None:
            return None
        for runtime in self._runtimes.values():
            if runtime.coordinator.local_device is device:
                return runtime
        return None


def patch_vacuum_class(
    cls: type,
    links: AreaCleaningLinks,
    clean_area_feature: int,
    make_segment: Callable[..., Any],
) -> bool:
    """Make a vacuum entity class support area cleaning for linked vacuums.

    @param make_segment: Home Assistant's Segment, called with id and name.
    @return: Whether the class is patched.
    """
    if getattr(cls, _PATCHED, False):
        return True
    original_features = cls.__dict__.get("supported_features")
    if not isinstance(original_features, property) or any(
        name in cls.__dict__ for name in ("async_get_segments", "async_clean_segments")
    ):
        # Changed internals, or Tuya Local now supports area cleaning itself
        return False
    original_get_segments = cls.async_get_segments
    original_clean_segments = cls.async_clean_segments

    def supported_features(self):
        features = original_features.fget(self)
        if links.runtime_for(self) is not None:
            features |= clean_area_feature
        return features

    async def async_get_segments(self):
        runtime = links.runtime_for(self)
        if runtime is None:
            return await original_get_segments(self)
        data = runtime.coordinator.data
        if data is None:
            return []
        return [
            make_segment(id=segment_id, name=name)
            for segment_id, name in rooms_as_segments(data.rooms, data.map_order)
        ]

    async def async_clean_segments(self, segment_ids, **kwargs):
        runtime = links.runtime_for(self)
        if runtime is None:
            await original_clean_segments(self, segment_ids, **kwargs)
            return
        await runtime.coordinator.async_clean_segments(
            segment_ids, runtime.clean_passes
        )

    cls.supported_features = property(supported_features)
    cls.async_get_segments = async_get_segments
    cls.async_clean_segments = async_clean_segments
    setattr(cls, _PATCHED, True)
    return True


_links = AreaCleaningLinks()
# Whether Tuya Local's vacuum class is patched, or it can't be
_patched = False
_patch_failed = False


async def async_link(hass, entry_id: str, runtime: Any) -> None:
    """Give the entry's Tuya Local vacuum area cleaning, if it can be done."""
    _links.add(entry_id, runtime)
    if await _async_patch(hass):
        _write_state(hass, runtime)


def unlink(hass, entry_id: str, runtime: Any) -> None:
    """Take area cleaning away from the entry's Tuya Local vacuum."""
    _links.remove(entry_id)
    _write_state(hass, runtime)


async def _async_patch(hass) -> bool:
    """Patch Tuya Local's vacuum class, once; return whether it's patched."""
    global _patched, _patch_failed  # pylint: disable=global-statement
    if _patched:
        return True
    if _patch_failed or not hass.config_entries.async_entries(TUYA_LOCAL_DOMAIN):
        return False
    try:
        # Area cleaning is only in recent Home Assistant versions
        from homeassistant.components.vacuum import (  # pylint: disable=import-outside-toplevel
            Segment,
            VacuumEntityFeature,
        )

        clean_area = VacuumEntityFeature.CLEAN_AREA
        module = sys.modules.get(TUYA_LOCAL_VACUUM_MODULE)
        if module is None:
            module = await hass.async_add_import_executor_job(
                importlib.import_module, TUYA_LOCAL_VACUUM_MODULE
            )
        patched = patch_vacuum_class(
            getattr(module, TUYA_LOCAL_VACUUM_CLASS), _links, clean_area, Segment
        )
    except (ImportError, AttributeError) as err:
        patched = False
        reason = str(err)
    else:
        reason = "its vacuum entity has changed"
    _patched = patched
    if not patched:
        _patch_failed = True
        _LOGGER.warning(
            "Area cleaning can't be added to Tuya Local's vacuum: %s", reason
        )
    return patched


def _write_state(hass, runtime: Any) -> None:
    """Update the Tuya Local vacuum's state, which lists its features."""
    if not _patched or not runtime.tuya_local_object_id:
        return
    # pylint: disable-next=import-outside-toplevel
    from homeassistant.components.vacuum import DATA_COMPONENT

    component = hass.data.get(DATA_COMPONENT)
    entity = component and component.get_entity(
        f"vacuum.{runtime.tuya_local_object_id}"
    )
    if entity is not None and entity.hass is not None:
        entity.async_write_ha_state()

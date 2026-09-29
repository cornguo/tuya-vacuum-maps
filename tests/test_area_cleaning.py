"""Tests for adding area cleaning to Tuya Local's vacuum, with fake classes."""

import asyncio
from dataclasses import dataclass, field
import importlib
from pathlib import Path
import sys
from types import ModuleType

import pytest

# area_cleaning imports its sibling modules, so load it from a stand-in package
# for the integration: its real __init__ requires Home Assistant.
_PACKAGE = "tuya_vacuum_maps_without_home_assistant"
if _PACKAGE not in sys.modules:
    package = ModuleType(_PACKAGE)
    package.__path__ = [
        str(Path(__file__).parent.parent / "custom_components" / "tuya_vacuum_maps")
    ]
    sys.modules[_PACKAGE] = package
area_cleaning = importlib.import_module(f"{_PACKAGE}.area_cleaning")

# Home Assistant's VacuumEntityFeature values
STATE = 4096
CLEAN_AREA = 16384


@dataclass
class Segment:
    """Stand in for Home Assistant's Segment."""

    id: str
    name: str


class FakeStateVacuumEntity:
    """Stand in for Home Assistant's StateVacuumEntity."""

    async def async_get_segments(self):
        raise NotImplementedError

    async def async_clean_segments(self, segment_ids, **kwargs):
        raise NotImplementedError


def _tuya_local_vacuum_class() -> type:
    """Return a new class shaped like Tuya Local's TuyaLocalVacuum."""

    class TuyaLocalVacuum(FakeStateVacuumEntity):
        def __init__(self, device) -> None:
            self._device = device

        @property
        def supported_features(self):
            return STATE

    return TuyaLocalVacuum


@dataclass
class FakeMapData:
    rooms: dict[int, str]
    map_order: list[int]


@dataclass
class FakeCoordinator:
    local_device: object
    data: FakeMapData | None
    cleaned: list = field(default_factory=list)

    async def async_clean_segments(self, segment_ids, clean_passes):
        self.cleaned.append((segment_ids, clean_passes))


@dataclass
class FakeRuntime:
    coordinator: FakeCoordinator
    clean_passes: int = 1


ROOMS = FakeMapData(rooms={0: "Kitchen", 1: "Bedroom", 2: "Hall"}, map_order=[2, 0])


def _patched(device) -> tuple[type, area_cleaning.AreaCleaningLinks, FakeRuntime]:
    """Return a patched class, its links and a runtime linked to the device."""
    cls = _tuya_local_vacuum_class()
    links = area_cleaning.AreaCleaningLinks()
    runtime = FakeRuntime(FakeCoordinator(device, ROOMS), clean_passes=2)
    links.add("entry", runtime)
    assert area_cleaning.patch_vacuum_class(cls, links, CLEAN_AREA, Segment)
    return cls, links, runtime


def test_rooms_are_segments_in_map_order():
    """Segments follow the map, with rooms missing from its order last."""
    assert area_cleaning.rooms_as_segments(ROOMS.rooms, ROOMS.map_order) == [
        ("2", "Hall"),
        ("0", "Kitchen"),
        ("1", "Bedroom"),
    ]


def test_segments_become_rooms_still_on_the_map():
    """Unknown, removed or repeated segments are skipped, keeping the order."""
    assert area_cleaning.room_ids_from_segments(
        ["1", "9", "x", "0", "1"], ROOMS.rooms
    ) == [1, 0]


def test_linked_vacuum_supports_area_cleaning():
    """Only the vacuum on a linked device gets area cleaning."""
    device = object()
    cls, _, _ = _patched(device)
    assert cls(device).supported_features == STATE | CLEAN_AREA
    assert cls(object()).supported_features == STATE


def test_linked_vacuum_reports_the_rooms():
    """The map's rooms are the vacuum's segments."""
    device = object()
    cls, _, _ = _patched(device)
    segments = asyncio.run(cls(device).async_get_segments())
    assert segments == [
        Segment("2", "Hall"),
        Segment("0", "Kitchen"),
        Segment("1", "Bedroom"),
    ]


def test_other_vacuums_keep_their_segments_methods():
    """An unlinked vacuum still uses Home Assistant's methods."""
    cls, _, _ = _patched(object())
    with pytest.raises(NotImplementedError):
        asyncio.run(cls(object()).async_get_segments())
    with pytest.raises(NotImplementedError):
        asyncio.run(cls(object()).async_clean_segments(["0"]))


def test_cleaning_segments_uses_the_clean_passes():
    """Area cleaning cleans the segments with the passes slider's value."""
    device = object()
    cls, _, runtime = _patched(device)
    asyncio.run(cls(device).async_clean_segments(["1", "0"]))
    assert runtime.coordinator.cleaned == [(["1", "0"], 2)]


def test_unlinked_vacuum_loses_area_cleaning():
    """Unloading the entry takes area cleaning away."""
    device = object()
    cls, links, _ = _patched(device)
    links.remove("entry")
    assert cls(device).supported_features == STATE


def test_patching_twice_patches_once():
    """A second entry doesn't wrap the class again."""
    device = object()
    cls, links, _ = _patched(device)
    assert area_cleaning.patch_vacuum_class(cls, links, CLEAN_AREA, Segment)
    assert cls(device).supported_features == STATE | CLEAN_AREA


def test_changed_tuya_local_class_isnt_patched():
    """The patch backs off if Tuya Local's vacuum isn't as expected."""
    links = area_cleaning.AreaCleaningLinks()

    class FixedFeatures(FakeStateVacuumEntity):
        supported_features = STATE

    class OwnAreaCleaning(_tuya_local_vacuum_class()):
        async def async_get_segments(self):
            return []

    OwnAreaCleaning.supported_features = property(lambda self: STATE)

    for cls in (FixedFeatures, OwnAreaCleaning):
        assert not area_cleaning.patch_vacuum_class(cls, links, CLEAN_AREA, Segment)

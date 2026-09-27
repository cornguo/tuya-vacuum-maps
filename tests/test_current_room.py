"""Tests for finding the room the vacuum is in."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

# Load the module by path so the test doesn't import the integration package,
# whose __init__ requires Home Assistant.
_SPEC = importlib.util.spec_from_file_location(
    "current_room",
    Path(__file__).parent.parent
    / "custom_components"
    / "tuya_vacuum_maps"
    / "current_room.py",
)
current_room = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(current_room)

WALL = 1
BACKGROUND = 255


def _layout() -> SimpleNamespace:
    """A 30 x 10 layout: room 1 on the left, a wall, room 2, then open space.

    The map origin is at (5, 5).
    """
    row = [1 << 2] * 10 + [WALL] + [2 << 2] * 9 + [BACKGROUND] * 10
    return SimpleNamespace(
        width=30,
        height=10,
        origin_x=5,
        origin_y=5,
        _map_data_array=bytes(row * 10),
        rooms=[SimpleNamespace(id=1), SimpleNamespace(id=2)],
    )


def _at(x: float, y: float) -> list[dict]:
    """A path ending at a layout position, in coordinates from the origin."""
    return [{"x": 0, "y": 0}, {"x": x - 5, "y": y - 5}]


def test_vacuum_in_a_room():
    """The room of the pixel under the end of the path."""
    assert current_room.current_room(_layout(), _at(3, 4)) == 1
    assert current_room.current_room(_layout(), _at(14.4, 4)) == 2


def test_vacuum_on_a_wall_is_in_the_closest_room():
    """On a wall pixel, e.g. docked, the nearest room pixel counts."""
    # Column 10 is the wall; room 2 starts right of it, room 1 left of it
    assert current_room.current_room(_layout(), _at(10, 4)) in (1, 2)
    layout = _layout()
    layout._map_data_array = bytes(
        ([1 << 2] * 10 + [WALL] * 3 + [2 << 2] * 7 + [BACKGROUND] * 10) * 10
    )
    assert current_room.current_room(layout, _at(12, 4)) == 2


def test_vacuum_far_from_rooms_is_in_none():
    """Beyond the search radius from any room there's no current room."""
    assert current_room.current_room(_layout(), _at(29, 4)) is None


def test_rooms_not_listed_and_empty_paths_are_ignored():
    """Pixels of rooms missing from the room info, or no path, give None."""
    layout = _layout()
    layout.rooms = [SimpleNamespace(id=1)]

    assert current_room.current_room(layout, _at(16, 4)) is None
    assert current_room.current_room(_layout(), []) is None

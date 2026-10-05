"""Tests for the fixed room parser."""

import importlib.util
from pathlib import Path

# Load the module by path so the test doesn't import the integration package,
# whose __init__ requires Home Assistant.
_SPEC = importlib.util.spec_from_file_location(
    "room_parser",
    Path(__file__).parent.parent
    / "custom_components"
    / "tuya_vacuum_maps"
    / "room_parser.py",
)
room_parser = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(room_parser)


def _room(room_id: int, name: str, vertices: list[tuple[int, int]]) -> bytes:
    """Build the bytes of one room in a map room array."""
    info = room_id.to_bytes(2, "big") + bytes(24)
    name_bytes = name.encode()
    return (
        info
        + bytes([len(name_bytes)])
        + name_bytes.ljust(19, b"\0")
        + bytes([len(vertices)])
        + b"".join(
            x.to_bytes(2, "big", signed=True) + y.to_bytes(2, "big", signed=True)
            for x, y in vertices
        )
    )


def test_rooms_after_one_with_vertices_are_parsed():
    """Each room is read after the previous room's vertices."""
    data = (
        bytes([1, 3])
        + _room(5, "Kitchen", [(-128, 300), (-1000, -2), (620, -384)])
        + _room(7, "Bedroom", [(10, 20)])
        + _room(9, "Hall", [])
    ).hex()

    rooms = room_parser.parse_map_room_array(data)

    assert [(room.id, room.name, room.vertex_num) for room in rooms] == [
        (5, "Kitchen", 3),
        (7, "Bedroom", 1),
        (9, "Hall", 0),
    ]


def test_name_ends_at_nul_despite_junk_after_it():
    """A name is cut at its NUL, even when the bytes after it aren't UTF-8."""
    room = _room(5, "", [(1, 2)])
    # Name length 3, then "1", NUL and a byte that isn't valid UTF-8
    room = room[:26] + bytes([3, 0x31, 0x00, 0xA2]) + room[30:]

    rooms = room_parser.parse_map_room_array((bytes([1, 1]) + room).hex())

    assert [(room.id, room.name, room.vertex_num) for room in rooms] == [(5, "1", 1)]

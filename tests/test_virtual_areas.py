"""Tests for reading and drawing virtual walls and zones."""

import base64
import importlib.util
from pathlib import Path
import struct

from PIL import Image
import pytest

# Load the module by path so the test doesn't import the integration package,
# whose __init__ requires Home Assistant.
_SPEC = importlib.util.spec_from_file_location(
    "virtual_areas",
    Path(__file__).parent.parent
    / "custom_components"
    / "tuya_vacuum_maps"
    / "virtual_areas.py",
)
virtual_areas = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(virtual_areas)


def _frame(payload: bytes) -> bytes:
    """Wrap a command and its data in a protocol version 0 frame."""
    return bytes([0xAA, 0x00, len(payload)]) + payload + bytes([sum(payload) & 0xFF])


def _points(*points: tuple[int, int]) -> bytes:
    return b"".join(struct.pack(">hh", x, y) for x, y in points)


# Walls report with the data of encodeVirtualWall0x12 in Tuya's
# @ray-js/robot-protocol for the wall (10, 20)-(30, 40) with origin (100, 200)
WALLS = _frame(bytes.fromhex("1301fc7b0708fd430640"))
# One rectangular zone from (10, -20) to (30, -40) around the origin
ZONES = _frame(
    bytes([0x1B, 1, 0, 4]) + _points((100, 200), (300, 200), (300, 400), (100, 400))
)
# A zone with negative stored values, which Tuya's decodeVirtualArea0x1b in
# @ray-js/robot-protocol decodes to (-1.4, 2), (3, 2), (3, -4) and (-1.4, -4)
NEGATIVE_ZONES = _frame(
    bytes([0x1B, 1, 0, 4]) + _points((-15, -21), (30, -21), (30, 40), (-15, 40))
)


def _value(*frames: bytes) -> str:
    return base64.b64encode(b"".join(frames)).decode()


def test_walls_and_zones_are_read_from_their_frames():
    """Points are divided by 10 and y flipped to point down, like the map."""
    areas = virtual_areas.VirtualAreas()

    # Another report before them, as in the vacuum's command_trans value
    virtual_areas.update_virtual_areas(
        areas, _value(_frame(bytes([0x17])), WALLS, ZONES)
    )

    # As decodeVirtualWall0x13 decodes it: the wall's end points, minus the origin
    assert areas.walls == [((-90.0, -180.0), (-70.0, -160.0))]
    assert areas.zones == [[(10.0, -20.0), (30.0, -20.0), (30.0, -40.0), (10.0, -40.0)]]


def test_negative_values_are_decoded_like_tuya():
    """Negative stored values are one's complement, as in Tuya's decoder."""
    areas = virtual_areas.VirtualAreas()

    virtual_areas.update_virtual_areas(areas, _value(NEGATIVE_ZONES))

    assert areas.zones == [[(-1.4, 2.0), (3.0, 2.0), (3.0, -4.0), (-1.4, -4.0)]]


def test_areas_not_reported_are_kept():
    """A value without the zones frame leaves the known zones in place."""
    areas = virtual_areas.VirtualAreas()
    virtual_areas.update_virtual_areas(areas, _value(ZONES))

    virtual_areas.update_virtual_areas(areas, _value(WALLS))
    virtual_areas.update_virtual_areas(areas, "")

    assert len(areas.zones) == 1
    assert len(areas.walls) == 1


@pytest.mark.parametrize("value", ["", _value(b"\x00\x01\x02"), _value(b"\xaa\x00\x09\x13")])
def test_malformed_values_are_ignored(value):
    """Empty values, other data and truncated frames give no frames."""
    assert virtual_areas.parse_frames(value) == {}


def test_zones_are_drawn_half_transparent_red():
    """A zone blends 50% red into the map; the rest is unchanged."""
    blue = (0, 0, 255)
    image = Image.new("RGB", (40, 40), blue)
    areas = virtual_areas.VirtualAreas(zones=[[(1, 1), (3, 1), (3, 3), (1, 3)]])

    # Origin (1, 1) in a 10 x 10 layout drawn 4 times larger
    virtual_areas.draw_virtual_areas(image, areas, (1, 1), 10)

    red, _, blue_part = image.getpixel((12, 12))
    assert (red, blue_part) == pytest.approx((128, 127), abs=1)
    assert image.getpixel((2, 2)) == blue
    assert image.getpixel((30, 30)) == blue


def test_areas_outside_the_image_are_clipped():
    """Zones partly or wholly off the map don't fail."""
    image = Image.new("RGB", (40, 40), (0, 0, 255))
    areas = virtual_areas.VirtualAreas(
        zones=[[(-5, -5), (2, -5), (2, 2), (-5, 2)], [(50, 50), (60, 50), (60, 60)]],
        walls=[((-20, 0), (20, 0))],
    )

    virtual_areas.draw_virtual_areas(image, areas, (0, 0), 10)

    assert image.getpixel((4, 4))[0] > 0
    assert image.size == (40, 40)


def test_nothing_to_draw_keeps_the_image():
    """Without walls and zones the image is left unchanged."""
    image = Image.new("RGB", (4, 4))

    virtual_areas.draw_virtual_areas(image, virtual_areas.VirtualAreas(), (0, 0), 4)

    assert image.getcolors() == [(16, (0, 0, 0))]

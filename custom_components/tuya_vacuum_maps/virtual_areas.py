"""Read virtual walls and no-go zones, and draw them on the map.

The vacuum reports them in its `command_trans` data point, as frames of Tuya's
laser robot vacuum protocol (version 0):

    aa 00 <length> <command> <data...> <checksum>

- 0x13, virtual walls: <count>, then per wall its two end points
- 0x1b, zones: <count>, then per zone <type> <corner count> and its corners

Each point is a signed 16-bit x and y relative to the map origin, times 10,
with y pointing up (see encodeVirtualWall0x12 in Tuya's @ray-js/robot-protocol
package).
"""

import base64
from dataclasses import dataclass, field
import struct

from PIL import Image, ImageDraw

WALLS_COMMAND = 0x13
ZONES_COMMAND = 0x1B

# 50% transparent red
COLOR = (255, 0, 0, 128)
# Width of a virtual wall, in layout pixels
WALL_WIDTH = 0.5

Point = tuple[float, float]


@dataclass
class VirtualAreas:
    """Virtual walls and zones, in map coordinates relative to the origin."""

    walls: list[tuple[Point, Point]] = field(default_factory=list)
    zones: list[list[Point]] = field(default_factory=list)


def parse_frames(value: str) -> dict[int, bytes]:
    """Return the data of each command in a base64 `command_trans` value."""
    raw = base64.b64decode(value) if value else b""
    frames = {}
    i = 0
    while i + 4 <= len(raw) and raw[i] == 0xAA:
        length = raw[i + 2]
        payload = raw[i + 3 : i + 3 + length]
        if len(payload) < length or not payload:
            break
        frames[payload[0]] = payload[1:]
        i += 4 + length
    return frames


def _point(data: bytes, offset: int) -> Point:
    x, y = struct.unpack_from(">hh", data, offset)
    return x / 10, -y / 10


def decode_walls(data: bytes) -> list[tuple[Point, Point]]:
    """Decode the virtual walls of a 0x13 frame."""
    count = data[0] if data else 0
    return [(_point(data, 1 + i * 8), _point(data, 5 + i * 8)) for i in range(count)]


def decode_zones(data: bytes) -> list[list[Point]]:
    """Decode the zones of a 0x1b frame."""
    zones = []
    offset = 1
    for _ in range(data[0] if data else 0):
        corners = data[offset + 1]
        offset += 2
        zones.append([_point(data, offset + i * 4) for i in range(corners)])
        offset += corners * 4
    return zones


def update_virtual_areas(areas: VirtualAreas, command_trans: str) -> None:
    """Update the areas from a `command_trans` value.

    The value holds the vacuum's latest reports, which don't always include
    the walls or zones, so each is only replaced when reported.
    """
    frames = parse_frames(command_trans)
    if WALLS_COMMAND in frames:
        areas.walls = decode_walls(frames[WALLS_COMMAND])
    if ZONES_COMMAND in frames:
        areas.zones = decode_zones(frames[ZONES_COMMAND])


def draw_virtual_areas(
    image: Image.Image, areas: VirtualAreas, origin: Point, layout_width: int
) -> Image.Image:
    """Return the image with the zones and walls drawn over it."""
    if not areas.walls and not areas.zones:
        return image

    scale = image.width / layout_width
    origin_x, origin_y = origin

    def to_image(point: Point) -> Point:
        return ((origin_x + point[0]) * scale, (origin_y + point[1]) * scale)

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for zone in areas.zones:
        if len(zone) >= 3:
            draw.polygon([to_image(point) for point in zone], fill=COLOR)
    for start, end in areas.walls:
        draw.line(
            [to_image(start), to_image(end)],
            fill=COLOR,
            width=max(1, round(WALL_WIDTH * scale)),
        )

    return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")

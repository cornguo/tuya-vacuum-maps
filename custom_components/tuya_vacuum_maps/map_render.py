"""Render the vacuum map.

tuya-vacuum's VacuumMap.to_image draws the dock marker at the map origin, which
is only where the map's coordinates start. The layout header has the dock's
position (pile_x, pile_y), so render_map draws the same map with the dock there.
Path width, colours and marker sizes are read from tuya-vacuum, so changes made
to them (see path_style.py) still apply.
"""

import copy
from dataclasses import dataclass
import io
from pathlib import Path

from PIL import Image, ImageDraw
from tuya_vacuum.vacuum_map import VacuumMap
import tuya_vacuum.vacuum_map_path as path_style

from .current_room import current_room
from .room_labels import (
    FONT_FILE_NAME,
    draw_room_labels,
    room_label_positions,
    rooms_in_map_order,
)
from .virtual_areas import VirtualAreas, draw_virtual_areas

# Rooms whose labels are within this fraction of the map height of each other
# count as one row when ordering rooms as they appear on the map
ROW_HEIGHT_FRACTION = 1 / 15


@dataclass
class MapData:
    """The latest map of the vacuum."""

    image: bytes
    # Room names by room id
    rooms: dict[int, str]
    # Room ids as they appear on the map, top left to bottom right
    map_order: list[int]
    # Id of the room the vacuum is in, if any
    current_room: int | None = None


class MapRenderer:
    """Render map files into MapData, reusing the last result if unchanged.

    Rendering takes over 100 ms of CPU, while the files rarely change when the
    vacuum is idle.
    """

    def __init__(self, font_cache_dir: Path, parse_map=VacuumMap) -> None:
        """Initialize the renderer.

        @param parse_map: Makes a tuya-vacuum VacuumMap from the hex layout and
            path files; replaceable in tests.
        """
        self._font_cache_dir = font_cache_dir
        self._parse_map = parse_map
        self._last_inputs = None
        self._last_data: MapData | None = None

    def render(
        self, layout: str | None, path: str | None, areas: VirtualAreas
    ) -> MapData:
        """Return the map of the hex layout and path files, with the areas."""
        # The font changes the labels once it has been downloaded
        font_ready = (self._font_cache_dir / FONT_FILE_NAME).exists()
        inputs = (layout, path, copy.deepcopy(areas), font_ready)
        if self._last_data is not None and inputs == self._last_inputs:
            return self._last_data

        vacuum_map = self._parse_map(layout, path)
        map_layout = vacuum_map.layout
        image = render_map(vacuum_map)
        draw_virtual_areas(
            image, areas, (map_layout.origin_x, map_layout.origin_y), map_layout.width
        )
        rooms = {}
        map_order = []
        room_id = None
        # Only version 1 layouts carry room info
        if map_layout.version == 1:
            draw_room_labels(image, map_layout, self._font_cache_dir)
            rooms = {
                room.id: room.name.rstrip("\0") or f"Room {room.id}"
                for room in map_layout.rooms
            }
            map_order = rooms_in_map_order(
                room_label_positions(map_layout),
                map_layout.height * ROW_HEIGHT_FRACTION,
            )
            room_id = current_room(map_layout, vacuum_map.path._path_data)

        image_bytes = io.BytesIO()
        image.save(image_bytes, format="PNG")
        self._last_inputs = inputs
        self._last_data = MapData(image_bytes.getvalue(), rooms, map_order, room_id)
        return self._last_data


def render_map(vacuum_map) -> Image.Image:
    """Return the image of a tuya-vacuum VacuumMap."""
    layout = vacuum_map.layout
    scale = path_style.PATH_SCALE

    image = layout.to_image()
    image = image.resize(
        (image.width * scale, image.height * scale), resample=Image.Resampling.NEAREST
    )
    draw = ImageDraw.Draw(image)

    # The path's points are relative to the map origin
    points = [
        ((point["x"] + layout.origin_x) * scale, (point["y"] + layout.origin_y) * scale)
        for point in vacuum_map.path._path_data
    ]
    if len(points) >= 2:
        draw.line(
            points, fill=path_style.PATH_COLOR, width=path_style.PATH_WIDTH, joint="curve"
        )

    _marker(
        draw,
        (layout.pile_x * scale, layout.pile_y * scale),
        path_style.PATH_CHARGER_MARKER_RADIUS,
        path_style.PATH_CHARGER_MARKER_COLOR,
        path_style.PATH_CHARGER_MARKER_OUTLINE_RADIUS,
        path_style.PATH_CHARGER_MARKER_OUTLINE_COLOR,
    )
    # The vacuum is at the end of its path
    if points:
        _marker(
            draw,
            points[-1],
            path_style.PATH_VACUUM_MARKER_RADIUS,
            path_style.PATH_VACUUM_MARKER_COLOR,
            path_style.PATH_VACUUM_MARKER_OUTLINE_RADIUS,
            path_style.PATH_VACUUM_MARKER_OUTLINE_COLOR,
        )

    return image


def _marker(draw, centre, radius, color, outline_radius, outline_color) -> None:
    """Draw a round marker with an outline."""
    draw.circle(centre, outline_radius, fill=outline_color)
    draw.circle(centre, radius, fill=color)

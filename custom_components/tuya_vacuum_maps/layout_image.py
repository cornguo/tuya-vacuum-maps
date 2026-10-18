"""Render the layout of a vacuum map.

tuya-vacuum's VacuumMapLayout.to_image prints "Unknown pixel type: None" for
every pixel whose value isn't in its table, which floods the Home Assistant log
with thousands of lines per map, and looks up colours one pixel at a time.
layout_image draws the same colours through a lookup table instead, and logs
the unknown values once at debug level.
"""

import logging

import numpy as np
from PIL import Image, ImageColor
from tuya_vacuum.const import ORIGIN_MAP_COLOR, pixel_types

_LOGGER = logging.getLogger(__name__)

# Colours tuya-vacuum gives the pixel types
BACKGROUND_COLOR = ImageColor.getcolor("#006ee6", "RGB")
WALL_COLOR = (50, 50, 50)
OBSTACLE_COLOR = (200, 200, 200)
# Colour tuya-vacuum gives pixels of an unknown type, or of a room it has no
# info for
UNKNOWN_COLOR = (20, 20, 20)


def layout_image(layout) -> Image.Image:
    """Return the image of a tuya-vacuum VacuumMapLayout, one pixel per pixel."""
    colors = {
        "bg_color": BACKGROUND_COLOR,
        "wall_color": WALL_COLOR,
        "fun_color": OBSTACLE_COLOR,
    }
    for room in layout.rooms:
        colors[f"room_color_{room.id}"] = ImageColor.getcolor(
            ORIGIN_MAP_COLOR[room.id % len(ORIGIN_MAP_COLOR)], "RGB"
        )

    palette = np.array(
        [
            colors.get(pixel_types.v1.get(value), UNKNOWN_COLOR)
            for value in range(256)
        ],
        dtype=np.uint8,
    )
    pixels = np.frombuffer(bytes(layout._map_data_array), dtype=np.uint8)[
        : layout.width * layout.height
    ].reshape(layout.height, layout.width)

    if _LOGGER.isEnabledFor(logging.DEBUG):
        unknown = sorted(
            value for value in np.unique(pixels) if value not in pixel_types.v1
        )
        if unknown:
            _LOGGER.debug("Layout has pixel values of unknown type: %s", unknown)

    return Image.fromarray(palette[pixels])

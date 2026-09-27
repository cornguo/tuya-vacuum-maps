"""Adjust how tuya-vacuum draws the cleaning path."""

import tuya_vacuum.vacuum_map_path

# Width of the cleaning path line, in pixels of the rendered image. tuya-vacuum
# draws it 8 px wide, a whole map cell, which hides the rooms beneath it.
PATH_WIDTH = 3


def apply() -> None:
    """Set the path width tuya-vacuum draws with."""
    tuya_vacuum.vacuum_map_path.PATH_WIDTH = PATH_WIDTH

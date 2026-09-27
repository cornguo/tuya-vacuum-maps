"""Tests for the cleaning path style."""

import importlib.util
from pathlib import Path

from tuya_vacuum.vacuum_map_path import VacuumMapPath

# Load the module by path so the test doesn't import the integration package,
# whose __init__ requires Home Assistant.
_SPEC = importlib.util.spec_from_file_location(
    "path_style",
    Path(__file__).parent.parent
    / "custom_components"
    / "tuya_vacuum_maps"
    / "path_style.py",
)
path_style = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(path_style)


def test_path_is_drawn_with_the_configured_width():
    """A horizontal path line is PATH_WIDTH pixels tall."""
    path_style.apply()
    path = VacuumMapPath.__new__(VacuumMapPath)
    path._path_data = [{"x": 0, "y": 10}, {"x": 20, "y": 10}]

    image = path.to_image(40, 20, (0, 0))

    # A column halfway along the line, away from the markers at its ends
    column = [image.getpixel((80, y)) for y in range(image.height)]
    assert sum(1 for pixel in column if pixel[3]) == path_style.PATH_WIDTH

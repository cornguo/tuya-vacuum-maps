"""Tests for rendering the map."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

# Load the module by path so the test doesn't import the integration package,
# whose __init__ requires Home Assistant.
_SPEC = importlib.util.spec_from_file_location(
    "map_render",
    Path(__file__).parent.parent
    / "custom_components"
    / "tuya_vacuum_maps"
    / "map_render.py",
)
map_render = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(map_render)

GREEN = (0, 128, 0)
BLUE = (0, 0, 255)
BACKGROUND = (50, 50, 50)


def _map(path_points: list[dict]) -> SimpleNamespace:
    """A 40 x 40 layout with its origin at (10, 10) and the dock at (30, 30)."""
    layout = SimpleNamespace(
        width=40,
        height=40,
        origin_x=10,
        origin_y=10,
        pile_x=30,
        pile_y=30,
        to_image=lambda: Image.new("RGB", (40, 40), BACKGROUND),
    )
    return SimpleNamespace(layout=layout, path=SimpleNamespace(_path_data=path_points))


def _pixel(image: Image.Image, x: float, y: float) -> tuple:
    """Return the pixel at a layout position."""
    scale = map_render.path_style.PATH_SCALE
    return image.getpixel((round(x * scale), round(y * scale)))


def test_dock_is_drawn_where_the_vacuum_reports_it():
    """The dock marker is at pile_x/pile_y, not at the map origin."""
    image = map_render.render_map(_map([]))

    assert _pixel(image, 30, 30) == GREEN
    assert _pixel(image, 10, 10) == BACKGROUND


def test_vacuum_is_drawn_at_the_end_of_its_path():
    """Path points are relative to the origin; the vacuum is at the last."""
    image = map_render.render_map(_map([{"x": 0, "y": 0}, {"x": 10, "y": 0}]))

    assert _pixel(image, 20, 10) == BLUE
    # The path line between the points
    assert _pixel(image, 13, 10) not in (BACKGROUND, GREEN, BLUE)

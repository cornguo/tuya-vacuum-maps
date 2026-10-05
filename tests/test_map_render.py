"""Tests for rendering the map."""

import importlib
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

from PIL import Image

# map_render imports its sibling modules, so load it from a stand-in package
# for the integration: its real __init__ requires Home Assistant.
_PACKAGE = "tuya_vacuum_maps_without_home_assistant"
if _PACKAGE not in sys.modules:
    package = ModuleType(_PACKAGE)
    package.__path__ = [
        str(Path(__file__).parent.parent / "custom_components" / "tuya_vacuum_maps")
    ]
    sys.modules[_PACKAGE] = package
map_render = importlib.import_module(f"{_PACKAGE}.map_render")
virtual_areas = importlib.import_module(f"{_PACKAGE}.virtual_areas")

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


def test_vacuum_position_is_the_end_of_its_path():
    """As fractions of the 40 x 40 image, with the origin at (10, 10)."""
    vacuum_map = _map([{"x": 0, "y": 0}, {"x": 10, "y": -6}])

    assert map_render.vacuum_position(vacuum_map) == (0.5, 0.1)


def test_vacuum_position_is_the_dock_without_a_path():
    """Without a path the vacuum is on the dock at (30, 30)."""
    assert map_render.vacuum_position(_map([])) == (0.75, 0.75)


def test_rendered_map_has_the_vacuum_position_and_an_image_id(tmp_path):
    """The image id changes with the image."""
    renderer = map_render.MapRenderer(tmp_path, parse_map=CountingParser())
    areas = virtual_areas.VirtualAreas()

    first = renderer.render("aa", "bb", areas)
    areas.zones.append([(0, 0), (20, 0), (20, 20)])
    second = renderer.render("aa", "bb", areas)

    assert first.vacuum_position == (0.75, 0.75)
    assert len(first.image_id) == 12
    assert second.image_id != first.image_id


class CountingParser:
    """Stand in for tuya-vacuum's VacuumMap, counting how often it's used."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, layout: str, path: str) -> SimpleNamespace:
        self.calls += 1
        vacuum_map = _map([])
        # A version 0 layout has no rooms to label
        vacuum_map.layout.version = 0
        return vacuum_map


def test_unchanged_map_is_not_rendered_again(tmp_path):
    """The same files and areas give the last result without parsing."""
    parser = CountingParser()
    renderer = map_render.MapRenderer(tmp_path, parse_map=parser)
    areas = virtual_areas.VirtualAreas()

    first = renderer.render("aa", "bb", areas)
    second = renderer.render("aa", "bb", areas)

    assert second is first
    assert parser.calls == 1


def test_changes_render_the_map_again(tmp_path):
    """New files, changed areas or a downloaded font render again."""
    parser = CountingParser()
    renderer = map_render.MapRenderer(tmp_path, parse_map=parser)
    areas = virtual_areas.VirtualAreas()
    renderer.render("aa", "bb", areas)

    renderer.render("aa", "cc", areas)
    # Areas are updated in place by the coordinator
    areas.zones.append([(0, 0), (1, 0), (1, 1)])
    renderer.render("aa", "cc", areas)
    (tmp_path / map_render.FONT_FILE_NAME).write_bytes(b"font")
    renderer.render("aa", "cc", areas)

    assert parser.calls == 4

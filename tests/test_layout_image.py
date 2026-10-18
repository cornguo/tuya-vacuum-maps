"""Tests for drawing the layout of a map."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

from tuya_vacuum.vacuum_map_layout import VacuumMapLayout

# Load the module by path so the test doesn't import the integration package,
# whose __init__ requires Home Assistant.
_SPEC = importlib.util.spec_from_file_location(
    "layout_image",
    Path(__file__).parent.parent
    / "custom_components"
    / "tuya_vacuum_maps"
    / "layout_image.py",
)
layout_image = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(layout_image)

LAYOUT_FILE = Path(__file__).parent / "layout.bin"


def test_layout_is_drawn_as_tuya_vacuum_draws_it():
    """The image of a real layout matches tuya-vacuum's own."""
    layout = VacuumMapLayout(LAYOUT_FILE.read_bytes().hex())

    image = layout_image.layout_image(layout)

    assert image.tobytes() == layout.to_image().tobytes()


def test_unknown_pixels_are_drawn_without_printing(capsys):
    """Values tuya-vacuum has no type for get its fallback colour, silently."""
    # 2 is not in tuya-vacuum's table; 255 is background
    layout = SimpleNamespace(
        width=2, height=1, rooms=[], _map_data_array=bytes([2, 255])
    )

    image = layout_image.layout_image(layout)

    assert image.getpixel((0, 0)) == layout_image.UNKNOWN_COLOR
    assert image.getpixel((1, 0)) == layout_image.BACKGROUND_COLOR
    assert capsys.readouterr().out == ""

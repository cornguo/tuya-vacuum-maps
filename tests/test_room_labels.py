"""Tests for drawing room labels."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

# Load the module by path so the test doesn't import the integration package,
# whose __init__ requires Home Assistant.
_SPEC = importlib.util.spec_from_file_location(
    "room_labels",
    Path(__file__).parent.parent
    / "custom_components"
    / "tuya_vacuum_maps"
    / "room_labels.py",
)
room_labels = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(room_labels)

WALL = 1
BACKGROUND = 255


def _layout() -> SimpleNamespace:
    """Build a 7x6 layout with a square room 0 and an L-shaped room 2."""
    rows = [[BACKGROUND] * 7 for _ in range(6)]
    for x, y in [(5, 0), (6, 0), (5, 1), (6, 1)]:
        rows[y][x] = 0
    for y in range(6):
        rows[y][0] = 2 << 2
    for x in range(1, 7):
        rows[5][x] = 2 << 2
    rows[2][3] = WALL
    return SimpleNamespace(
        width=7,
        height=6,
        _map_data_array=bytes(value for row in rows for value in row),
        rooms=[
            SimpleNamespace(id=0, name="Hall\0\0"),
            SimpleNamespace(id=2, name="Kitchen"),
            # Listed in the room info but has no pixels
            SimpleNamespace(id=5, name="Gone"),
        ],
    )


def test_labels_are_placed_inside_their_rooms():
    """Each label is on a pixel of its own room, NUL padding removed."""
    labels = room_labels.room_label_positions(_layout())

    assert labels == [
        (0, "Hall", (5, 0)),
        # The L's centre (1.75, 3.75) is outside it; use its closest room pixel
        (2, "Kitchen", (2, 5)),
    ]


def test_rooms_with_the_same_name_each_get_a_label():
    """Rooms are labelled by id, so duplicate names aren't merged."""
    layout = _layout()
    layout.rooms[1].name = "Hall"

    labels = room_labels.room_label_positions(layout)

    assert [(room_id, name) for room_id, name, _ in labels] == [
        (0, "Hall"),
        (2, "Hall"),
    ]


def test_label_text_shows_name_and_id():
    """The label is the room name with its id on the next line."""
    assert room_labels.label_text(2, "Kitchen") == "Kitchen\n(ID: 2)"
    assert room_labels.label_text(2, "") == "(ID: 2)"


def test_labels_are_drawn_on_the_scaled_image(tmp_path):
    """Drawing ASCII labels changes the image without downloading a font."""
    image = Image.new("RGB", (7 * 8, 6 * 8), "blue")

    room_labels.draw_room_labels(image, _layout(), tmp_path)

    assert image.getcolors() != [(7 * 8 * 6 * 8, (0, 0, 255))]
    assert not list(tmp_path.iterdir())


def test_font_with_wrong_checksum_is_not_used(tmp_path, monkeypatch):
    """A download that doesn't match the pinned checksum is discarded."""
    monkeypatch.setattr(room_labels, "_font_failed_at", None)
    monkeypatch.setattr(
        room_labels.httpx,
        "get",
        lambda *args, **kwargs: room_labels.httpx.Response(
            200, content=b"not a font", request=room_labels.httpx.Request("GET", "x")
        ),
    )

    assert room_labels.ensure_font(tmp_path) is None
    assert not list(tmp_path.iterdir())


def test_cached_font_is_used_without_download(tmp_path, monkeypatch):
    """An already downloaded font is returned without a request."""
    (tmp_path / room_labels.FONT_FILE_NAME).write_bytes(b"font")
    monkeypatch.setattr(room_labels.httpx, "get", None)

    assert room_labels.ensure_font(tmp_path) == tmp_path / room_labels.FONT_FILE_NAME

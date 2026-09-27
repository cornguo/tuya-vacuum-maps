"""Draw room names on a rendered vacuum map."""

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from tuya_vacuum.vacuum_map_layout import VacuumMapLayout

# Font size of a label, in layout pixels
LABEL_SIZE = 4


def room_label_positions(
    layout: VacuumMapLayout,
) -> list[tuple[int, str, tuple[int, int]]]:
    """Return the id, name and label position of each room, in layout pixels.

    In a version 1 layout, a floor pixel of room N has the value N << 2. The
    label goes on the room's centre, or on the room pixel closest to it when the
    centre falls outside the room (e.g. an L-shaped room).
    """
    pixels = np.frombuffer(bytes(layout._map_data_array), dtype=np.uint8).reshape(
        layout.height, layout.width
    )

    labels = []
    for room in layout.rooms:
        ys, xs = np.nonzero(pixels == room.id << 2)
        if not len(xs):
            continue
        centre_x, centre_y = xs.mean(), ys.mean()
        closest = np.argmin((xs - centre_x) ** 2 + (ys - centre_y) ** 2)
        name = room.name.rstrip("\0")
        labels.append((room.id, name, (int(xs[closest]), int(ys[closest]))))

    return labels


def label_text(room_id: int, name: str) -> str:
    """Return the text of a room's label."""
    return f"{name}\n(ID: {room_id})" if name else f"(ID: {room_id})"


def draw_room_labels(image: Image.Image, layout: VacuumMapLayout) -> None:
    """Draw each room's name and id on the image rendered from the layout."""
    labels = room_label_positions(layout)
    scale = image.width / layout.width
    size = LABEL_SIZE * scale

    font = ImageFont.load_default(size=size)

    draw = ImageDraw.Draw(image)
    stroke_width = max(1, round(scale / 3))

    for room_id, name, (x, y) in labels:
        text = label_text(room_id, name)
        # Centre the text block on the position; placed by its bounding box
        # since multiline anchors differ between Pillow versions
        left, top, right, bottom = draw.multiline_textbbox(
            (0, 0), text, font=font, align="center", stroke_width=stroke_width
        )
        draw.multiline_text(
            (
                (x + 0.5) * scale - (left + right) / 2,
                (y + 0.5) * scale - (top + bottom) / 2,
            ),
            text,
            font=font,
            align="center",
            fill="white",
            stroke_width=stroke_width,
            stroke_fill="black",
        )

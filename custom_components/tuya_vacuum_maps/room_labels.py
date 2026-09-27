"""Draw room names on a rendered vacuum map."""

import hashlib
import logging
import os
import time
from pathlib import Path

import httpx
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from tuya_vacuum.vacuum_map_layout import VacuumMapLayout

_LOGGER = logging.getLogger(__name__)

# Font size of a label, in layout pixels
LABEL_SIZE = 4

# Pillow's default font has no CJK glyphs, so room names outside ASCII are drawn
# with Noto Sans TC (SIL Open Font License), downloaded once on first use.
FONT_URL = (
    "https://cdn.jsdelivr.net/gh/notofonts/noto-cjk"
    "@165c01b46ea533872e002e0785ff17e44f6d97d8"
    "/Sans/SubsetOTF/TC/NotoSansTC-Medium.otf"
)
FONT_SHA256 = "bf206dca0975779bac71cb49a037a364156ca98a0c431b1b7d6b29fb8952ac7e"
FONT_FILE_NAME = "NotoSansTC-Medium.otf"

# Seconds to wait before retrying a failed font download
FONT_RETRY_INTERVAL = 3600

_font_failed_at: float | None = None


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


def ensure_font(cache_dir: Path) -> Path | None:
    """Return the path of the CJK font, downloading it if needed.

    Returns None if the font isn't available, e.g. while offline; the download
    is then retried after FONT_RETRY_INTERVAL.
    """
    global _font_failed_at  # pylint: disable=global-statement

    path = cache_dir / FONT_FILE_NAME
    if path.exists():
        return path
    if _font_failed_at and time.monotonic() - _font_failed_at < FONT_RETRY_INTERVAL:
        return None

    try:
        _LOGGER.info("Downloading font for room names from %s", FONT_URL)
        response = httpx.get(FONT_URL, follow_redirects=True, timeout=60)
        response.raise_for_status()
        if hashlib.sha256(response.content).hexdigest() != FONT_SHA256:
            raise ValueError("Downloaded font doesn't match its expected checksum")
        cache_dir.mkdir(parents=True, exist_ok=True)
        partial_path = path.with_suffix(".part")
        partial_path.write_bytes(response.content)
        os.replace(partial_path, path)
    except (httpx.HTTPError, OSError, ValueError) as err:
        _LOGGER.warning("Could not download font for room names: %s", err)
        _font_failed_at = time.monotonic()
        return None

    return path


def draw_room_labels(
    image: Image.Image, layout: VacuumMapLayout, font_cache_dir: Path
) -> None:
    """Draw each room's name and id on the image rendered from the layout."""
    labels = room_label_positions(layout)
    scale = image.width / layout.width
    size = LABEL_SIZE * scale

    font_path = None
    if any(not name.isascii() for _, name, _ in labels):
        font_path = ensure_font(font_cache_dir)
    if font_path:
        font = ImageFont.truetype(str(font_path), size)
    else:
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

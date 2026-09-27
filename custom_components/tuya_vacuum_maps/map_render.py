"""Render the vacuum map, with the dock where the vacuum reports it.

tuya-vacuum's VacuumMap.to_image draws the dock marker at the map origin, which
is only where the map's coordinates start. The layout header has the dock's
position (pile_x, pile_y), so this renders the same map with the dock there.
Path width, colours and marker sizes are read from tuya-vacuum, so changes made
to them (see path_style.py) still apply.
"""

from PIL import Image, ImageDraw

import tuya_vacuum.vacuum_map_path as path_style


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

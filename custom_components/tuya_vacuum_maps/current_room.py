"""Find the room the vacuum is in."""

import numpy as np

# How far from the vacuum a room still counts, in layout pixels (5 cm each on
# the tested map). A docked vacuum sits on the wall at a room's edge.
SEARCH_RADIUS = 5


def current_room(layout, path_points: list[dict]) -> int | None:
    """Return the id of the room at the vacuum's position, if any.

    The vacuum is at the end of its path, whose points are relative to the map
    origin. In a version 1 layout, a floor pixel of room N has the value N << 2.
    When the vacuum isn't on a floor pixel, e.g. on its dock against a wall,
    the closest room pixel within SEARCH_RADIUS is used.
    """
    if not path_points:
        return None
    x = round(layout.origin_x + path_points[-1]["x"])
    y = round(layout.origin_y + path_points[-1]["y"])

    pixels = np.frombuffer(bytes(layout._map_data_array), dtype=np.uint8).reshape(
        layout.height, layout.width
    )
    left, top = max(0, x - SEARCH_RADIUS), max(0, y - SEARCH_RADIUS)
    window = pixels[top : y + SEARCH_RADIUS + 1, left : x + SEARCH_RADIUS + 1]

    room_ids = [room.id for room in layout.rooms]
    ys, xs = np.nonzero(((window & 3) == 0) & np.isin(window >> 2, room_ids))
    if not len(xs):
        return None
    closest = np.argmin((xs + left - x) ** 2 + (ys + top - y) ** 2)
    return int(window[ys[closest], xs[closest]] >> 2)

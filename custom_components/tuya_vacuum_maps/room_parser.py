"""Fix room parsing in the tuya-vacuum library.

`VacuumMapRoom.parse_map_room_array` in tuya-vacuum steps from one room to the
next by the fixed-size room header only, without skipping that room's vertices.
Every room after the first is then read from the middle of the previous room's
vertex data.
"""

from tuya_vacuum.vacuum_map_room import INFO_BYTE_LEN, NAME_BYTE_LEN, VacuumMapRoom

# Length of the fixed part of a room: properties, name and vertex count (hex chars)
ROOM_HEADER_HEX_LENGTH = (INFO_BYTE_LEN + NAME_BYTE_LEN + 1) * 2

# Each vertex is an x and a y coordinate of 2 bytes each (hex chars)
VERTEX_HEX_LENGTH = 2 * 2 * 2


def parse_map_room_array(data: str) -> list[VacuumMapRoom]:
    """Parse the map room array.

    @param data: The `map_room_array`.
    """

    rooms = []
    room_count = int(data[2:4], 16)

    byte_pos = 2 * 2  # "region_num"

    for _ in range(room_count):
        room = VacuumMapRoom(data, byte_pos)
        rooms.append(room)
        byte_pos += ROOM_HEADER_HEX_LENGTH + room.vertex_num * VERTEX_HEX_LENGTH

    return rooms


def apply() -> None:
    """Replace the library's room parser with the fixed one."""
    VacuumMapRoom.parse_map_room_array = staticmethod(parse_map_room_array)

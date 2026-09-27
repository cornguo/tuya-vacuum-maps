"""Build the command that makes the vacuum clean selected rooms.

The command is a frame sent through the `command_trans` data point, in the
format of Tuya's laser robot vacuum protocol (see `encodeRoomClean0x14` in
Tuya's @ray-js/robot-protocol package):

    aa 00 <length> 14 <passes> <room count> <room id>... <checksum>

`00` is protocol version 0, which the vacuum uses in its own reports. The length
counts the bytes from `14` through the last room id, and the checksum is their
sum, keeping the lowest byte.
"""

import base64

FRAME_HEADER = 0xAA
PROTOCOL_VERSION = 0x00
ROOM_CLEAN_COMMAND = 0x14

# Cleaning passes the Tuya app offers
MIN_CLEAN_PASSES = 1
MAX_CLEAN_PASSES = 3


def encode_room_clean(room_ids: list[int], clean_passes: int) -> bytes:
    """Return the frame that cleans the given rooms."""
    if not room_ids:
        raise ValueError("At least one room is needed")
    if not MIN_CLEAN_PASSES <= clean_passes <= MAX_CLEAN_PASSES:
        raise ValueError(f"Invalid number of cleaning passes: {clean_passes}")

    payload = bytes([ROOM_CLEAN_COMMAND, clean_passes, len(room_ids), *room_ids])
    return (
        bytes([FRAME_HEADER, PROTOCOL_VERSION, len(payload)])
        + payload
        + bytes([sum(payload) & 0xFF])
    )


def room_clean_commands(room_ids: list[int], clean_passes: int) -> list[dict]:
    """Return the device commands that start cleaning the given rooms."""
    frame = encode_room_clean(room_ids, clean_passes)
    return [
        {"code": "command_trans", "value": base64.b64encode(frame).decode()},
        {"code": "mode", "value": "selectroom"},
    ]

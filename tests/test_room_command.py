"""Tests for the room clean command."""

import base64
import importlib.util
from pathlib import Path

import pytest

# Load the modules by path so the tests don't import the integration package,
# whose __init__ requires Home Assistant.
_DIR = Path(__file__).parent.parent / "custom_components" / "tuya_vacuum_maps"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, _DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


room_command = _load("room_command")


@pytest.mark.parametrize(
    ("room_ids", "clean_passes", "frame"),
    [
        # Output of encodeRoomClean0x14 in Tuya's @ray-js/robot-protocol with
        # version "0"; the first was also accepted by a Hitachi RV-X20DPA
        ([0], 1, "aa00041401010016"),
        ([0, 2], 1, "aa0005140102000219"),
        # Rooms stay in the given order
        ([2, 0], 3, "aa000514030202001b"),
    ],
)
def test_frame_matches_tuya_encoder(room_ids, clean_passes, frame):
    """The frame has Tuya's header, length, command and checksum."""
    assert room_command.encode_room_clean(room_ids, clean_passes).hex() == frame


def test_commands_select_room_mode():
    """The frame is sent base64 encoded, with the room cleaning mode."""
    commands = room_command.room_clean_commands([0], 1)

    assert commands == [
        {"code": "command_trans", "value": "qgAEFAEBABY="},
        {"code": "mode", "value": "selectroom"},
    ]
    assert base64.b64decode(commands[0]["value"]).hex() == "aa00041401010016"


@pytest.mark.parametrize(
    ("room_ids", "clean_passes"), [([], 1), ([0], 0), ([0], 4)]
)
def test_invalid_commands_are_rejected(room_ids, clean_passes):
    """No rooms or passes outside 1-3 aren't sent to the vacuum."""
    with pytest.raises(ValueError):
        room_command.encode_room_clean(room_ids, clean_passes)



def test_commands_as_local_data_point_values():
    """Commands are keyed by data point number for Tuya Local."""
    commands = room_command.room_clean_commands([0], 1)

    assert room_command.commands_as_dp_values(
        commands, {"command_trans": 15, "mode": 4}
    ) == {15: "qgAEFAEBABY=", 4: "selectroom"}
    # A vacuum without a known number for a code can't be commanded locally
    assert room_command.commands_as_dp_values(commands, {"command_trans": 15}) is None


def test_map_upload_request():
    """The vacuum is asked for both its map and path, by code or locally."""
    commands = room_command.map_upload_commands()

    assert commands == [{"code": "request", "value": "get_both"}]
    assert room_command.commands_as_dp_values(commands, {"request": 16}) == {
        16: "get_both"
    }

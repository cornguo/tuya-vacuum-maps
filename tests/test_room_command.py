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
cloud_commands = _load("cloud_commands")


@pytest.mark.parametrize(
    ("room_ids", "clean_passes", "frame"),
    [
        # Output of encodeRoomClean0x14 in Tuya's @ray-js/robot-protocol with
        # version "0"; the first was also accepted by a Hitachi RV-X20DP
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


def test_signature_covers_the_body():
    """Commands are signed with the hash of their body, unlike GET requests."""
    args = ("id", "secret", "token", "1700000000000", "nonce", "POST")

    assert cloud_commands.sign(*args, '{"a":1}', "/p") != cloud_commands.sign(
        *args, '{"a":2}', "/p"
    )
    # Tuya's documented string to sign, with the SHA-256 of the body
    assert cloud_commands.sign(*args, "", "/p") == cloud_commands.hmac.new(
        b"secret",
        (
            "idtoken1700000000000noncePOST\n"
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855\n\n/p"
        ).encode(),
        "sha256",
    ).hexdigest().upper()

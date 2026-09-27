"""Tests for using Tuya Local's connection, with a fake Tuya Local device."""

import asyncio
import importlib
from pathlib import Path
import sys
from types import ModuleType

# local_device imports its sibling modules, so load it from a stand-in package
# for the integration: its real __init__ requires Home Assistant.
_PACKAGE = "tuya_vacuum_maps_without_home_assistant"
if _PACKAGE not in sys.modules:
    package = ModuleType(_PACKAGE)
    package.__path__ = [
        str(Path(__file__).parent.parent / "custom_components" / "tuya_vacuum_maps")
    ]
    sys.modules[_PACKAGE] = package
local_device = importlib.import_module(f"{_PACKAGE}.local_device")

DEVICE_ID = "vacuum"


class FakeTuyaLocalDevice:
    """Stand in for Tuya Local's device: a cache of data points it received."""

    def __init__(self, state: dict[str, object]) -> None:
        self.state = state
        self.sent: list[dict] = []

    def get_property(self, dps_id: str):
        return self.state.get(dps_id)

    async def async_set_properties(self, properties: dict) -> None:
        self.sent.append(properties)


def _hass_data(device) -> dict:
    """hass.data as Tuya Local fills it for a set up device."""
    return {"tuya_local": {DEVICE_ID: {"device": device, "tuyadevice": object()}}}


def test_data_points_are_read_from_tuya_locals_cache():
    """Values come from Tuya Local by their number, as strings keys."""
    local = local_device.LocalVacuum(
        _hass_data(FakeTuyaLocalDevice({"5": "charge_done"})), DEVICE_ID
    )

    assert local.available
    assert local.get(5) == "charge_done"
    assert local.get(15) is None


def test_values_are_sent_through_tuya_local():
    """Commands go through Tuya Local's device, keyed by number as strings."""
    device = FakeTuyaLocalDevice({})
    local = local_device.LocalVacuum(_hass_data(device), DEVICE_ID)

    assert asyncio.run(local.async_set({15: "qgA=", 4: "selectroom"}))
    assert device.sent == [{"15": "qgA=", "4": "selectroom"}]


def test_without_tuya_local_nothing_is_used():
    """Without Tuya Local, or without this vacuum in it, callers use the cloud."""
    for hass_data in ({}, {"tuya_local": {}}, {"tuya_local": {"other": {}}}):
        local = local_device.LocalVacuum(hass_data, DEVICE_ID)
        assert not local.available
        assert local.get(5) is None
        assert not asyncio.run(local.async_set({4: "selectroom"}))


def test_a_failing_tuya_local_is_not_used_again():
    """A changed Tuya Local, e.g. a missing method, switches to the cloud."""

    class ChangedDevice:
        def get_property(self, dps_id):
            raise AttributeError("renamed")

    local = local_device.LocalVacuum(_hass_data(ChangedDevice()), DEVICE_ID)

    assert local.get(5) is None
    assert not local.available
    assert not asyncio.run(local.async_set({4: "selectroom"}))


def test_data_point_numbers_come_from_the_specification():
    """Codes are mapped to numbers from both the status and function lists."""
    specification = {
        "status": [{"code": "status", "dp_id": 5}, {"code": "no_number"}],
        "functions": [{"code": "command_trans", "dp_id": 15}],
    }

    assert local_device.dp_ids_from_specification(specification) == {
        "status": 5,
        "command_trans": 15,
    }

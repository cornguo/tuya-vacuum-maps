"""Tests for how often the map is fetched."""

import importlib.util
from pathlib import Path

import pytest

# Load the module by path so the test doesn't import the integration package,
# whose __init__ requires Home Assistant.
_SPEC = importlib.util.spec_from_file_location(
    "polling",
    Path(__file__).parent.parent
    / "custom_components"
    / "tuya_vacuum_maps"
    / "polling.py",
)
polling = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(polling)


@pytest.mark.parametrize("status", ["charging", "charge_done", "standby", "sleep"])
def test_idle_vacuum_is_polled_less_often(status):
    """A docked or idle vacuum doesn't need a map every 10 seconds."""
    assert polling.update_interval(status) == polling.IDLE_INTERVAL
    assert polling.IDLE_INTERVAL > polling.ACTIVE_INTERVAL


@pytest.mark.parametrize(
    "status", ["cleaning", "select_room", "goto_charge", "repositing", None, "new"]
)
def test_moving_or_unknown_vacuum_is_polled_often(status):
    """Cleaning, returning, or an unknown status keeps the fast interval."""
    assert polling.update_interval(status) == polling.ACTIVE_INTERVAL

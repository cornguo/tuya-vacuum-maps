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


from datetime import timedelta

DEFAULTS = polling.PollingIntervals()


@pytest.mark.parametrize("status", ["charging", "charge_done", "standby", "sleep"])
def test_idle_vacuum_is_polled_less_often(status):
    """A docked or idle vacuum doesn't need a map every 10 seconds."""
    assert DEFAULTS.for_status(status) == timedelta(seconds=60)


@pytest.mark.parametrize(
    "status", ["cleaning", "select_room", "goto_charge", "repositing", None, "new"]
)
def test_moving_or_unknown_vacuum_is_polled_often(status):
    """Cleaning, returning, or an unknown status keeps the fast interval."""
    assert DEFAULTS.for_status(status) == timedelta(seconds=10)


def test_entry_without_options_uses_the_defaults():
    """Entries created before the options existed keep 10 s / 60 s."""
    assert polling.PollingIntervals.from_options({}) == DEFAULTS


def test_intervals_come_from_the_options():
    """The options flow's values, in seconds, set both intervals."""
    intervals = polling.PollingIntervals.from_options(
        {polling.CONF_ACTIVE_INTERVAL: 5.0, polling.CONF_IDLE_INTERVAL: 300.0}
    )
    assert intervals.for_status("cleaning") == timedelta(seconds=5)
    assert intervals.for_status("charging") == timedelta(seconds=300)

"""Tests for the map type log filter."""

import importlib.util
import logging
from pathlib import Path

# Load the module by path so the test doesn't import the integration package,
# whose __init__ requires Home Assistant.
_SPEC = importlib.util.spec_from_file_location(
    "map_type_filter",
    Path(__file__).parent.parent
    / "custom_components"
    / "tuya_vacuum_maps"
    / "map_type_filter.py",
)
map_type_filter = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(map_type_filter)


def test_documented_map_types_are_not_logged(caplog):
    """Only map types Tuya doesn't document are still warned about."""
    map_type_filter.apply()
    logger = logging.getLogger("tuya_vacuum.vacuum")

    with caplog.at_level(logging.WARNING, logger="tuya_vacuum.vacuum"):
        for map_type in (2, 3, 4):
            logger.warning("Unknown map type: %s", map_type)

    assert [record.getMessage() for record in caplog.records] == [
        "Unknown map type: 4"
    ]

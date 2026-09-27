"""Talk to the vacuum through Tuya Local's connection, when it has one.

Tuya devices often accept only one or two local connections, and Tuya Local
keeps one open, so its device is reused instead of opening another. It's reached
through Tuya Local's internals (hass.data["tuya_local"][<device id>]["device"],
with get_property and async_set_properties), so callers fall back to the Tuya
Cloud API when it's missing or doesn't work.
"""

import logging
from typing import Any

from .const import TUYA_LOCAL_DOMAIN

_LOGGER = logging.getLogger(__name__)


def dp_ids_from_specification(specification: dict) -> dict[str, int]:
    """Return the data point number of each code in a v1.1 specification.

    The numbers differ between vacuum models, e.g. command_trans is 15 on some.
    """
    return {
        item["code"]: item["dp_id"]
        for kind in ("status", "functions")
        for item in specification.get(kind, [])
        if "dp_id" in item
    }


class LocalVacuum:
    """The vacuum's data points through Tuya Local."""

    def __init__(self, hass_data: dict, device_id: str) -> None:
        """Initialize with Home Assistant's hass.data and the vacuum's id."""
        self._hass_data = hass_data
        self._device_id = device_id
        self._failed = False

    def _device(self):
        """Return Tuya Local's device for the vacuum, if it's set up."""
        entry = self._hass_data.get(TUYA_LOCAL_DOMAIN, {}).get(self._device_id)
        return entry.get("device") if isinstance(entry, dict) else None

    @property
    def available(self) -> bool:
        """Return whether Tuya Local has the vacuum."""
        return not self._failed and self._device() is not None

    def get(self, dp_id: int) -> Any:
        """Return a data point's last value Tuya Local has, or None."""
        device = self._device()
        if device is None or self._failed:
            return None
        try:
            return device.get_property(str(dp_id))
        except Exception as err:  # pylint: disable=broad-except
            self._fail(err)
            return None

    async def async_set(self, values: dict[int, Any]) -> bool:
        """Send data point values; return False if it couldn't be done."""
        device = self._device()
        if device is None or self._failed:
            return False
        try:
            await device.async_set_properties(
                {str(dp_id): value for dp_id, value in values.items()}
            )
        except Exception as err:  # pylint: disable=broad-except
            self._fail(err)
            return False
        return True

    def _fail(self, err: Exception) -> None:
        """Stop using Tuya Local, e.g. after a change in its internals."""
        _LOGGER.warning(
            "Could not use Tuya Local's connection, using the Tuya Cloud API: %s",
            err,
        )
        self._failed = True

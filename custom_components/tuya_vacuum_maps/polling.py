"""How often to fetch the map, depending on what the vacuum is doing."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

# Options of the entry, in seconds
CONF_ACTIVE_INTERVAL = "active_interval"
CONF_IDLE_INTERVAL = "idle_interval"

# While the vacuum may be moving, e.g. cleaning or returning to its dock
DEFAULT_ACTIVE_SECONDS = 10
# While it's idle, when its map and position don't change
DEFAULT_IDLE_SECONDS = 60
# Range the options accept, so the Tuya Cloud isn't asked too often
MIN_INTERVAL_SECONDS = 5
MAX_INTERVAL_SECONDS = 3600

# Values of the vacuum's `status` data point when it isn't moving
IDLE_STATUSES = {"standby", "charging", "charge_done", "sleep"}


@dataclass(frozen=True)
class PollingIntervals:
    """Update intervals while the vacuum is active and idle."""

    active: timedelta = timedelta(seconds=DEFAULT_ACTIVE_SECONDS)
    idle: timedelta = timedelta(seconds=DEFAULT_IDLE_SECONDS)

    @classmethod
    def from_options(cls, options: Mapping[str, Any]) -> "PollingIntervals":
        """Return the intervals set in the entry's options, or the defaults."""
        return cls(
            active=timedelta(
                seconds=options.get(CONF_ACTIVE_INTERVAL, DEFAULT_ACTIVE_SECONDS)
            ),
            idle=timedelta(
                seconds=options.get(CONF_IDLE_INTERVAL, DEFAULT_IDLE_SECONDS)
            ),
        )

    def for_status(self, status: str | None) -> timedelta:
        """Return the update interval for the vacuum's status.

        An unknown status polls often, so a moving vacuum is never missed.
        """
        return self.idle if status in IDLE_STATUSES else self.active

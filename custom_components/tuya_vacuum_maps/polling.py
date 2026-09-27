"""How often to fetch the map, depending on what the vacuum is doing."""

from datetime import timedelta

# While the vacuum may be moving, e.g. cleaning or returning to its dock
ACTIVE_INTERVAL = timedelta(seconds=10)
# While it's idle, when its map and position don't change
IDLE_INTERVAL = timedelta(seconds=60)

# Values of the vacuum's `status` data point when it isn't moving
IDLE_STATUSES = {"standby", "charging", "charge_done", "sleep"}


def update_interval(status: str | None) -> timedelta:
    """Return the update interval for the vacuum's status.

    An unknown status polls often, so a moving vacuum is never missed.
    """
    return IDLE_INTERVAL if status in IDLE_STATUSES else ACTIVE_INTERVAL

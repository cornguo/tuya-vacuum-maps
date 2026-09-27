"""Silence tuya-vacuum's warning for map files it doesn't use.

The realtime map API returns up to four files, of which tuya-vacuum only uses
the layout map (0) and path map (1). It logs "Unknown map type" for the others
on every fetch, although Tuya documents them: 2 is the incremental path map and
3 is the planning map.
"""

import logging

# Map types documented by Tuya but not used by tuya-vacuum
IGNORED_MAP_TYPES = {2, 3}


class MapTypeFilter(logging.Filter):
    """Drop the "Unknown map type" warning for documented map types."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Return False for records that should not be logged."""
        return not (
            record.msg == "Unknown map type: %s"
            and record.args
            and record.args[0] in IGNORED_MAP_TYPES
        )


def apply() -> None:
    """Add the filter to tuya-vacuum's logger."""
    logging.getLogger("tuya_vacuum.vacuum").addFilter(MapTypeFilter())

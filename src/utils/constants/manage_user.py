from typing import Tuple

TEMP_BAN_DURATIONS: Tuple[Tuple[int, str], ...] = (
    (3600,   "1 hour"),
    (86400,  "1 day"),
    (604800, "7 days"),
)

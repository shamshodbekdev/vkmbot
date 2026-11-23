from typing import Tuple

BATCH_SIZE: int = 25
BATCH_DELAY: float = 1.2
SEND_DELAY: float = 0.05
MAX_SEND_RETRIES: int = 3

# Progress/control keys are kept for a week so the "View progress" button keeps working.
BROADCAST_STATE_TTL: int = 7 * 24 * 3600

BROADCAST_PROGRESS_ICONS: Tuple[Tuple[bool, str], ...] = (
    (True, "5454096630372379732"),
    (False, "5427009714745517609"),
)

# Labels are gettext msgids: translate them with _() when rendering.
BROADCAST_DELAYS: Tuple[Tuple[int, str], ...] = (
    (0, "Start now"),
    (3600, "1 hour later"),
    (10800, "3 hours later"),
    (21600, "6 hours later"),
    (43200, "12 hours later"),
    (86400, "24 hours later"),
)

BROADCAST_PAGE_SIZE: int = 10

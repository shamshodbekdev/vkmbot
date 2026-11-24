from typing import Tuple

# Users are read from the database in pages of BATCH_SIZE (keyset pagination) and
# sent in chunks of RATE_PER_SECOND messages per second, concurrently. Telegram
# allows ~30 messages/second for broadcasts; 25 leaves headroom for the bot's
# normal traffic. A "retry after" from Telegram pauses the whole broadcast.
BATCH_SIZE: int = 500
RATE_PER_SECOND: int = 25
MAX_SEND_RETRIES: int = 3
# How often the job edits the admin's progress message (seconds).
LIVE_UPDATE_INTERVAL: int = 10
# Custom schedule: the admin enters local time in this zone.
BROADCAST_TIMEZONE: str = "Asia/Tashkent"
MAX_SCHEDULE_DAYS: int = 60

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

import datetime
from database.models import User

UTC = datetime.timezone.utc


def is_temp_banned(user: User) -> bool:
    now = datetime.datetime.now(UTC)
    return user.blocked_until is not None and user.blocked_until > now

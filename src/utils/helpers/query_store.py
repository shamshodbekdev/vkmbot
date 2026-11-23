import hashlib
import re
from typing import Optional

from core.cache import cache
from utils.constants.youtube import MAX_QUERY_LENGTH, QUERY_TTL

_TOKEN_PATTERN = re.compile(r"^[0-9a-f]{16}$")


def _key(token: str) -> str:
    return "query:%s" % token


async def store_query(query: str) -> str:
    """Save a search query in Redis and return a short token for callback_data.

    Telegram limits callback_data to 64 bytes and aiogram forbids ':' inside
    values, so free-form user text can never be embedded in a button directly.
    """
    query = query.strip()[:MAX_QUERY_LENGTH]
    token = hashlib.sha1(query.encode("utf-8")).hexdigest()[:16]
    await cache.set(_key(token), query, ttl=QUERY_TTL)
    return token


async def load_query(token: str) -> Optional[str]:
    """Resolve a token created by :func:`store_query`.

    Buttons created before tokens were introduced carry the raw query, which is
    returned as-is. ``None`` means the token expired.
    """
    if not _TOKEN_PATTERN.match(token):
        return token or None
    return await cache.get(_key(token))

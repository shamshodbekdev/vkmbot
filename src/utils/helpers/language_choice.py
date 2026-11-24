"""Remembers which users have explicitly chosen a language.

``users.language_code`` is NOT NULL with a default, so it cannot tell "chosen"
from "never asked". A permanent Redis set (outside the cache namespace, so it
survives TELEGRAM_USERNAME changes) records the users who picked a language.
"""
import logging

from core.cache import cache

logger = logging.getLogger(__name__)

LANGUAGE_CHOSEN_KEY: str = "vkm:language_chosen"


async def has_chosen_language(telegram_id: int) -> bool:
    try:
        return bool(await cache.client.sismember(LANGUAGE_CHOSEN_KEY, telegram_id))
    except Exception as error:
        # Never lock users out because Redis is unavailable.
        logger.warning("Cannot read language choice for %s: %r", telegram_id, error)
        return True


async def mark_language_chosen(telegram_id: int) -> None:
    try:
        await cache.client.sadd(LANGUAGE_CHOSEN_KEY, telegram_id)
    except Exception as error:
        logger.warning("Cannot save language choice for %s: %r", telegram_id, error)

import logging
from typing import Any, Awaitable, Callable, Dict, Optional

from aiogram import BaseMiddleware
from aiogram.types import Update
from aiogram.types import User as TelegramUser
from aiogram.utils.i18n import gettext as _

from core.cache import cache
from core.config import config
from database.enums import UserRole
from database.models import User
from utils.constants.throttle import THROTTLE_LIMIT, THROTTLE_WINDOW

logger = logging.getLogger(__name__)


class ThrottlerMiddleware(BaseMiddleware):
    """Fixed-window rate limiter for messages and callback queries, stored in Redis.

    Allows ``limit`` updates per ``window`` seconds per Telegram user. The user is
    warned once per window; extra updates are dropped silently. Admins are never
    throttled. If Redis is unavailable the update is let through (fail-open), so
    the limiter can never take the bot down.
    """

    def __init__(self, limit: int = THROTTLE_LIMIT, window: int = THROTTLE_WINDOW) -> None:
        self.limit = limit
        self.window = window

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:
        if event.message is None and event.callback_query is None:
            return await handler(event, data)

        from_user: Optional[TelegramUser] = data.get("event_from_user")
        user: Optional[User] = data.get("user")
        if (
            from_user is None
            # Anonymous group admins / linked channels share one bot id across all chats.
            or from_user.is_bot
            or from_user.id == config.telegram_id
            or (user is not None and user.role == UserRole.ADMINISTRATOR and user.telegram_id == from_user.id)
        ):
            return await handler(event, data)

        key = "throttle:%d" % from_user.id
        try:
            hits = await cache.increment(key)
            if hits == 1:
                await cache.expire(key, self.window)
        except Exception:
            logger.exception("Throttler storage error, letting the update through")
            return await handler(event, data)

        if hits <= self.limit:
            return await handler(event, data)

        if hits == self.limit + 1:
            text = _("Too many requests. Please slow down.")
            if event.callback_query:
                await event.callback_query.answer(text=text, show_alert=True)
            elif event.message:
                await event.message.answer(text=text)
        elif event.callback_query:
            await event.callback_query.answer()
        return None

from typing import Any, Awaitable, Callable, Dict, Optional

from aiogram import BaseMiddleware
from aiogram.types import Update
from aiogram.utils.i18n import gettext as _

from core.config import config
from database.models import User
from utils.helpers.manage_user import is_temp_banned


class BlockedMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:
        user: Optional[User] = data.get("user")
        if user is None or user.telegram_id == config.telegram_id:
            return await handler(event, data)

        if not (user.is_blocked or is_temp_banned(user)):
            return await handler(event, data)

        text = _("You are blocked from using this bot. Please contact the administrator for more information.")
        if event.callback_query:
            await event.callback_query.answer(text=text, show_alert=True)
        elif event.message:
            await event.message.answer(text=text)
        elif event.inline_query:
            await event.inline_query.answer(results=[], cache_time=60, is_personal=True)
        return None

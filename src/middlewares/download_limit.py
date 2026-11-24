from typing import Any, Awaitable, Callable, Dict, Optional

from aiogram import BaseMiddleware, Bot
from aiogram.types import CallbackQuery, Message, TelegramObject
from aiogram.utils.i18n import gettext as _

from services.media_downloader import MAX_DOWNLOADS_PER_USER, queue_notifier, user_download_slot


class DownloadLimitMiddleware(BaseMiddleware):
    """Allows at most MAX_DOWNLOADS_PER_USER simultaneous downloads per user.

    Register it as an *inner* middleware on download routers: it then only runs
    for events a download handler actually matched, and holds the slot for the
    whole duration of that handler.

    It also tells the download layer how to reach the user: when every global
    download slot is busy, the request waits in a queue and the user gets a
    "you are in the queue" message, removed as soon as the download starts.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        from_user = data.get("event_from_user")
        async with user_download_slot(from_user.id if from_user else None) as allowed:
            if allowed:
                token = queue_notifier.set(self._notifier(event, data.get("bot")))
                try:
                    return await handler(event, data)
                finally:
                    queue_notifier.reset(token)
        text = _("⏳ You already have %(count)s downloads in progress. Please wait until they finish.") % dict(
            count=MAX_DOWNLOADS_PER_USER,
        )
        if isinstance(event, CallbackQuery):
            await event.answer(text, show_alert=True)
        elif isinstance(event, Message):
            await event.answer(text)
        return None

    @staticmethod
    def _notifier(event: TelegramObject, bot: Optional[Bot]) -> Optional[Callable[[], Awaitable[Any]]]:
        if isinstance(event, CallbackQuery):
            target = event.message if isinstance(event.message, Message) else None
        elif isinstance(event, Message):
            target = event
        else:
            return None
        if target is None:
            return None
        # Resolved now: the message is sent later, from inside the download call.
        text = _("⏳ You are in the queue. Please wait...")

        async def notify() -> Message:
            # Message.answer keeps the forum topic of the original message.
            return await target.answer(text=text)

        return notify

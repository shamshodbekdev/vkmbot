import datetime
from typing import Any, Awaitable, Callable, Dict, Optional

from aiogram import BaseMiddleware
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.types import Chat, Update
from aiogram.types import User as TelegramUser

from database.models import User

UTC = datetime.timezone.utc
ACTIVITY_TOUCH_INTERVAL = datetime.timedelta(minutes=5)
INACTIVE_STATUSES = (ChatMemberStatus.LEFT, ChatMemberStatus.KICKED)


class RegisterMiddleware(BaseMiddleware):
    """Creates/updates the DB record for the chat an update belongs to and puts it into ``data["user"]``.

    Private chats are stored by user id, groups and supergroups by chat id.
    Channels are ignored. Inline queries have no chat, so only an existing
    record is loaded for them (users who never started the bot are not created).
    """

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:
        from_user: Optional[TelegramUser] = data.get("event_from_user")
        chat: Optional[Chat] = data.get("event_chat")

        if chat is None:
            if event.inline_query is not None and from_user is not None:
                data["user"] = await User.get_or_none(telegram_id=from_user.id)
            return await handler(event, data)

        if chat.type == ChatType.CHANNEL:
            return await handler(event, data)

        is_private = chat.type == ChatType.PRIVATE
        if is_private and (from_user is None or from_user.is_bot):
            return await handler(event, data)

        # Group records depend only on the chat, so messages from anonymous admins
        # or linked channels (sent with a bot as from_user) are registered too.
        if is_private:
            telegram_id = from_user.id
            values = dict(
                chat_type=ChatType.PRIVATE,
                is_premium=bool(from_user.is_premium),
                display_name=(from_user.first_name or str(telegram_id))[:255],
            )
        else:
            telegram_id = chat.id
            values = dict(
                chat_type=ChatType(chat.type),
                is_premium=False,
                display_name=(chat.title or str(telegram_id))[:255],
            )

        user, created = await User.get_or_create(
            telegram_id=telegram_id,
            defaults=dict(values, chat_status=ChatMemberStatus.MEMBER),
        )
        if not created:
            # Activity proves the chat is reachable again; keep finer statuses
            # such as "administrator" set by the my_chat_member handlers.
            if user.chat_status in INACTIVE_STATUSES:
                values["chat_status"] = ChatMemberStatus.MEMBER
            changed = False
            for field, value in values.items():
                if getattr(user, field) != value:
                    setattr(user, field, value)
                    changed = True
            # updated_at doubles as "last activity" for statistics, so refresh it
            # periodically even when nothing else changed.
            stale = user.updated_at is None or user.updated_at < datetime.datetime.now(UTC) - ACTIVITY_TOUCH_INTERVAL
            if changed or stale:
                await user.save()

        data["user"] = user
        return await handler(event, data)

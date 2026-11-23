from aiogram.enums import ChatType
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message


class OnlyPrivate(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        message = event.message if isinstance(event, CallbackQuery) else event
        return message is not None and message.chat.type == ChatType.PRIVATE

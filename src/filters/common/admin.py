from typing import Optional

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from core.config import config
from database.enums import UserRole
from database.models import User


class IsAdmin(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery, user: Optional[User] = None) -> bool:
        # Admin rights are personal: in groups ``user`` is the group record, so
        # check the actual sender against the private-chat record instead.
        sender = event.from_user
        if sender is None:
            return False
        if sender.id == config.telegram_id:
            return True
        if user is None or user.telegram_id != sender.id:
            return False
        return user.role == UserRole.ADMINISTRATOR

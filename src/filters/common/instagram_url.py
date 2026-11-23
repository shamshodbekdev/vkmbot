from aiogram.filters import BaseFilter
from aiogram.types import Message

from utils.validators import extract_instagram_url


class InstagramUrlFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool | dict:
        url = extract_instagram_url(message.text or message.caption or "")
        if not url:
            return False
        return dict(instagram_url=url)

from aiogram.filters import BaseFilter
from aiogram.types import Message

from utils.validators import extract_tiktok_url


class TikTokUrlFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool | dict:
        url = extract_tiktok_url(message.text or message.caption or "")
        if not url:
            return False
        return dict(tiktok_url=url)

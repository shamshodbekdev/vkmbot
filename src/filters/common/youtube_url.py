from aiogram.filters import BaseFilter
from aiogram.types import Message

from utils.validators import extract_youtube_url


class YouTubeUrlFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool | dict:
        url = extract_youtube_url(message.text or message.caption or "")
        if not url:
            return False
        return dict(youtube_url=url)

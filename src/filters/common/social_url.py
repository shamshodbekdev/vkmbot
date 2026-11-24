from aiogram.filters import BaseFilter
from aiogram.types import Message

from utils.validators import extract_social_url


class SocialUrlFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool | dict:
        found = extract_social_url(message.text or message.caption or "")
        if not found:
            return False
        platform, url = found
        return dict(social_platform=platform, social_url=url)

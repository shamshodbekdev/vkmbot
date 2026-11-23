from typing import Optional

from schemas.instagram import InstagramResponseSchema
from services.instagram_api import InstagramAPI


class InstagramConvert:
    @classmethod
    async def convert(cls, url: str) -> Optional[InstagramResponseSchema]:
        """Download the post locally; each media ``url`` is a local file path."""
        return await InstagramAPI.fetch(url=url)

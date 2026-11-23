from typing import Optional

from schemas.tiktok import TikTokSchema
from services.tiktok_api import TikTokAPI


class TikTokConvert:
    @classmethod
    async def convert(cls, url: str) -> Optional[TikTokSchema]:
        """Metadata only (``play`` is None); call :meth:`download` to fetch the video."""
        return await TikTokAPI.info(url=url)

    @classmethod
    async def download(cls, url: str) -> Optional[TikTokSchema]:
        """Download the video locally; ``play`` is the local file path."""
        return await TikTokAPI.download(url=url)

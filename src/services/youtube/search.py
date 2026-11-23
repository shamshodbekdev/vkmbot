from typing import List

from schemas.youtube_search import SongSchema
from services.youtube_api import YouTubeAPI


class YouTubeSearch:
    @classmethod
    async def search(cls, query: str, limit: int, offset: int = 0, fallback: bool = False) -> List[SongSchema]:
        return await YouTubeAPI.search(query=query, limit=limit, offset=offset, fallback=fallback)

    @classmethod
    async def suggestions(cls, query: str) -> List[str]:
        return await YouTubeAPI.suggestions(query=query)

from typing import Dict, List

from schemas.mood import MoodItemSchema, MoodPlaylistItemSchema
from services.youtube_api import YouTubeAPI


class YouTubeMood:
    @classmethod
    async def moods(cls) -> Dict[str, List[MoodItemSchema]]:
        return await YouTubeAPI.moods()

    @classmethod
    async def playlists(cls, params: str) -> List[MoodPlaylistItemSchema]:
        return await YouTubeAPI.mood_playlists(params=params)

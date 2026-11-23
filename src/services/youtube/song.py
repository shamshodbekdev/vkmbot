from typing import Optional

from schemas.song_detail import SongDetailSchema
from services.youtube_api import YouTubeAPI


class YouTubeSong:
    @classmethod
    async def get(cls, video_id: str) -> Optional[SongDetailSchema]:
        return await YouTubeAPI.song(video_id=video_id)

from typing import Optional

from schemas.playlist import PlaylistSchema
from services.youtube_api import YouTubeAPI


class YouTubePlaylist:
    @classmethod
    async def get(
        cls,
        playlist_id: str,
        limit: int = 100,
        related: bool = False,
        suggestions_limit: int = 0,
    ) -> Optional[PlaylistSchema]:
        return await YouTubeAPI.playlist(
            playlist_id=playlist_id,
            limit=limit,
            related=related,
            suggestions_limit=suggestions_limit,
        )

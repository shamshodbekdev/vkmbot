from typing import Optional

from schemas.charts import ChartsSchema
from schemas.playlist import PlaylistSchema
from services.youtube.playlist import YouTubePlaylist
from services.youtube_api import YouTubeAPI


class YouTubeCharts:
    @classmethod
    async def get(cls, country: str = "ZZ") -> Optional[ChartsSchema]:
        return await YouTubeAPI.charts(country=country)

    @classmethod
    async def get_playlist(cls, country: str = "ZZ", limit: int = 100) -> Optional[PlaylistSchema]:
        """Return the chart playlist (with tracks) for a country, or None if unavailable."""
        charts = await cls.get(country=country)
        if not charts or not charts.videos:
            return None
        playlist_id = charts.videos[-1].playlistId
        if not playlist_id:
            return None
        return await YouTubePlaylist.get(playlist_id=playlist_id, limit=limit)

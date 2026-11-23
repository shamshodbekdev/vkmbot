from typing import Optional

from schemas.youtube_download import SongDownloadSchema
from services.youtube_api import YouTubeAPI


class YouTubeDownload:
    @classmethod
    async def get(cls, video_id: str) -> Optional[SongDownloadSchema]:
        """Download the track locally; ``link`` is the path of the MP3 file."""
        return await YouTubeAPI.download(video_id=video_id)

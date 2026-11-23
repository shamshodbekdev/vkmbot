"""Free, local Instagram downloader (yt-dlp + ffmpeg).

Handles posts, reels, IGTV and carousels with videos. Files are downloaded to
a temp directory and returned as local paths in ``InstagramResponseSchema``.

Instagram limits anonymous access, so some posts (photo-only posts, private or
age-restricted posts, or any post while this server's IP is rate-limited) need
a logged-in session. Export the cookies of a logged-in browser in Netscape
format to ``cookies/instagram.txt`` and yt-dlp will use them automatically.
"""
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from schemas.instagram import InstagramMediaItemSchema, InstagramResponseSchema
from services.media_downloader import base_options, downloaded_path, extract, fits_upload_limit, new_job_dir

logger = logging.getLogger(__name__)

_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}


def _entries(info: Dict[str, Any]) -> List[Dict[str, Any]]:
    entries = info.get("entries")
    return [e for e in entries if e] if entries else [info]


class InstagramAPI:
    @classmethod
    async def fetch(cls, url: str) -> Optional[InstagramResponseSchema]:
        job_dir = new_job_dir()
        options = base_options(job_dir, "instagram")
        options.update(
            noplaylist=False,  # carousels are playlists
            outtmpl="%(playlist_index|0)03d-%(id)s.%(ext)s",
            # Telegram-friendly MP4 (H.264 + AAC) when available.
            format="bv*[ext=mp4][vcodec^=avc]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b",
            merge_output_format="mp4",
        )
        info = await extract(url, options, download=True)
        if not info:
            logger.warning(
                "Instagram media unavailable for %s (photo-only, private, or login required; "
                "add cookies/instagram.txt to enable logged-in downloads)", url,
            )
            return None

        medias: List[InstagramMediaItemSchema] = []
        for entry in _entries(info):
            path: Optional[Path] = downloaded_path(entry)
            if not path or not fits_upload_limit(path):
                continue
            kind = "image" if path.suffix.lower() in _IMAGE_EXTENSIONS else "video"
            medias.append(InstagramMediaItemSchema(type=kind, url=str(path)))
        return InstagramResponseSchema(medias=medias)

"""Free, local TikTok downloader (yt-dlp).

``info`` reads the metadata only (cheap; lets the handler check its cache first),
``download`` fetches the video without watermark to a local temp file.
"""
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from schemas.tiktok import TikTokSchema
from services.media_downloader import MEDIA_TMP_DIR, base_options, downloaded_path, extract, fits_upload_limit, new_job_dir

logger = logging.getLogger(__name__)

# yt-dlp tags TikTok's watermarked "download_addr" format with a "watermarked" note:
# skip it ("?" keeps formats that have no note at all), and prefer H.264 because
# some Telegram clients cannot play H.265 (bytevc1).
_FORMAT = (
    "b[vcodec^=h264][format_note!*=?watermark]"
    "/b[format_note!*=?watermark]"
    "/b"
)


def _to_schema(info: Dict[str, Any], play: Optional[str] = None, size: Optional[int] = None) -> TikTokSchema:
    return TikTokSchema(
        id=str(info.get("id")) if info.get("id") else None,
        title=info.get("title") or info.get("description"),
        cover=info.get("thumbnail"),
        duration=int(info["duration"]) if info.get("duration") else None,
        play=play,
        size=size,
        play_count=info.get("view_count"),
        digg_count=info.get("like_count"),
        music_info=dict(
            title=info.get("track"),
            author=info.get("artist") or (info.get("artists") or [None])[0],
            album=info.get("album"),
        ),
        author=dict(
            id=str(info.get("uploader_id")) if info.get("uploader_id") else None,
            unique_id=info.get("uploader"),
            nickname=info.get("creator") or info.get("channel"),
        ),
    )


class TikTokAPI:
    @classmethod
    async def info(cls, url: str) -> Optional[TikTokSchema]:
        # Metadata only: nothing is written, so no job directory is needed.
        MEDIA_TMP_DIR.mkdir(parents=True, exist_ok=True)
        options = base_options(MEDIA_TMP_DIR, "tiktok")
        options.update(format=_FORMAT)
        info = await extract(url, options, download=False)
        return _to_schema(info) if info else None

    @classmethod
    async def download(cls, url: str) -> Optional[TikTokSchema]:
        job_dir = new_job_dir()
        options = base_options(job_dir, "tiktok")
        options.update(format=_FORMAT)
        info = await extract(url, options, download=True)
        if not info:
            return None
        path: Optional[Path] = downloaded_path(info)
        if not path or not fits_upload_limit(path):
            logger.warning("TikTok %s: no usable video file", url)
            return None
        return _to_schema(info, play=str(path), size=path.stat().st_size)

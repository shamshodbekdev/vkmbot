"""Free, local downloader for Pinterest, Snapchat and Likee.

Strategy per link:
1. Short links (pin.it, t.snapchat.com, l.likee.video) are resolved first.
2. yt-dlp downloads the video (best path: handles HLS/DASH and merging).
3. If yt-dlp fails, the public page is read and its Open Graph tags are used:
   ``og:video`` for videos (Snapchat Spotlight; yt-dlp's extractor is out of date)
   and ``og:image`` for image pins on Pinterest (yt-dlp only supports videos).
"""
import html
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

from services.media_downloader import (
    base_options,
    discard_dir,
    download_url,
    downloaded_path,
    FileTooLargeError,
    extract,
    fetch_text,
    fits_upload_limit,
    is_too_large,
    new_job_dir,
    resolve_url,
    size_aware_format,
)

logger = logging.getLogger(__name__)

_META_TAG = re.compile(r"<meta\s+[^>]*>", re.IGNORECASE)
_META_ATTR = re.compile(r'([\w:-]+)\s*=\s*"([^"]*)"')
_PINTEREST_SIZE = re.compile(r"/\d+x(\d+)?/")
_SHORT_HOSTS = {"pin.it", "t.snapchat.com", "l.likee.video"}

PLATFORMS = ("pinterest", "snapchat", "likee")


@dataclass
class SocialMedia:
    kind: str  # "video" | "photo"
    path: Path


def open_graph(page: str) -> Dict[str, str]:
    """Parse ``<meta property|name="og:..." content="...">`` tags (attribute order does not matter)."""
    tags: Dict[str, str] = {}
    for tag in _META_TAG.findall(page):
        attrs = {k.lower(): html.unescape(v) for k, v in _META_ATTR.findall(tag)}
        key = attrs.get("property") or attrs.get("name")
        content = attrs.get("content")
        if key and content and key.startswith("og:") and key not in tags:
            tags[key] = content
    return tags


def _extension(url: str, default: str) -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    return suffix if suffix in {".mp4", ".mov", ".jpg", ".jpeg", ".png", ".webp", ".gif"} else default


class SocialAPI:
    @classmethod
    async def fetch(cls, url: str, platform: str) -> List[SocialMedia]:
        if urlparse(url if "://" in url else "https://" + url).hostname in _SHORT_HOSTS:
            url = await resolve_url(url if "://" in url else "https://" + url)

        media = await cls._with_ytdlp(url, platform)
        if media:
            return media
        media = await cls._with_open_graph(url, platform)
        if not media:
            logger.warning("%s: nothing downloadable at %s", platform, url)
        return media

    @classmethod
    async def _with_ytdlp(cls, url: str, platform: str) -> List[SocialMedia]:
        job_dir = new_job_dir()
        options = base_options(job_dir, platform)
        options.update(format=size_aware_format(), merge_output_format="mp4")
        info = await extract(url, options, download=True)
        path = downloaded_path(info) if info else None
        if path and fits_upload_limit(path):
            return [SocialMedia("video", path)]
        discard_dir(job_dir)
        if is_too_large(info) or path:
            raise FileTooLargeError(url)
        return []

    @classmethod
    async def _with_open_graph(cls, url: str, platform: str) -> List[SocialMedia]:
        page = await fetch_text(url)
        if not page:
            return []
        og = open_graph(page)
        job_dir = new_job_dir()

        video_url = og.get("og:video:secure_url") or og.get("og:video") or og.get("og:video:url")
        if video_url:
            path = await download_url(video_url, job_dir / ("video%s" % _extension(video_url, ".mp4")))
            if path:
                return [SocialMedia("video", path)]

        image_url = og.get("og:image")
        if image_url and platform == "pinterest":
            # og:image is a resized copy (e.g. /736x/); the original lives under /originals/.
            candidates = [_PINTEREST_SIZE.sub("/originals/", image_url, count=1), image_url]
            for candidate in dict.fromkeys(candidates):
                path = await download_url(candidate, job_dir / ("image%s" % _extension(candidate, ".jpg")), queue=False)
                if path:
                    return [SocialMedia("photo", path)]
        discard_dir(job_dir)
        return []

from typing import List, Literal, Optional
from urllib.parse import urlparse

from schemas.instagram import InstagramResponseSchema

_SHORTCODE_MARKERS = {"p", "reel", "reels", "tv"}


def extract_shortcode(url: str) -> Optional[str]:
    parts = [p for p in urlparse(url).path.rstrip("/").split("/") if p]
    for i, part in enumerate(parts):
        if part in _SHORTCODE_MARKERS and i + 1 < len(parts):
            return parts[i + 1]
    return None


def _media_kind(type_: str) -> Optional[Literal["video", "photo"]]:
    val = (type_ or "").lower()
    if val == "video":
        return "video"
    if val == "image":
        return "photo"
    return None


def collect_media_items(response: InstagramResponseSchema) -> List[tuple]:
    items = []
    for item in response.medias:
        kind = _media_kind(item.type)
        if kind:
            items.append((item.url, item.thumbnail, kind))
    return items

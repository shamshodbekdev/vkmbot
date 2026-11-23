import re
from typing import Optional

INSTAGRAM_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?instagram\.com/"
    r"(?:"
    r"(?:p|reel|reels|tv)/[A-Za-z0-9_-]+"
    r"|[A-Za-z0-9_.]+/(?:p|reel|reels|tv)/[A-Za-z0-9_-]+"
    r"|s/[A-Za-z0-9_-]+"
    r")",
    re.IGNORECASE,
)


def extract_instagram_url(text: str) -> Optional[str]:
    match = INSTAGRAM_PATTERN.search(text)
    if not match:
        return None
    raw = match.group(0)
    return raw

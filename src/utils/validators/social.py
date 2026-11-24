import re
from typing import Optional, Tuple

_PATTERNS = (
    (
        "pinterest",
        re.compile(
            r"(?:https?://)?(?:[a-z]{2,3}\.)?(?:www\.)?pinterest\.[a-z.]{2,6}/pin/[\w-]+/?"
            r"|(?:https?://)?pin\.it/[\w-]+",
            re.IGNORECASE,
        ),
    ),
    (
        "snapchat",
        re.compile(
            r"(?:https?://)?(?:www\.)?snapchat\.com/(?:@[\w.-]+/)?spotlight/[\w-]+"
            r"|(?:https?://)?(?:www\.)?snapchat\.com/t/[\w-]+"
            r"|(?:https?://)?t\.snapchat\.com/[\w-]+",
            re.IGNORECASE,
        ),
    ),
    (
        "likee",
        re.compile(
            r"(?:https?://)?(?:www\.|l\.)?likee\.video/(?:@[\w.-]+/video/\d+|v/[\w-]+|[\w-]{5,})",
            re.IGNORECASE,
        ),
    ),
)


def extract_social_url(text: str) -> Optional[Tuple[str, str]]:
    """Return ``(platform, url)`` for the first Pinterest / Snapchat / Likee link in ``text``."""
    for platform, pattern in _PATTERNS:
        match = pattern.search(text or "")
        if match:
            url = match.group(0)
            return platform, url if url.lower().startswith("http") else "https://" + url
    return None

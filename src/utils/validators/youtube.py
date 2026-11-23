import re
from typing import Optional

YOUTUBE_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.|m\.|music\.)?"
    r"(?:"
    r"youtube\.com/(?:watch\?(?:[\w=&%-]*&)?v=|shorts/|live/|embed/)"
    r"|youtu\.be/"
    r")"
    r"[\w-]{11}",
    re.IGNORECASE,
)


def extract_youtube_url(text: str) -> Optional[str]:
    match = YOUTUBE_PATTERN.search(text)
    if not match:
        return None
    url = match.group(0)
    return url if url.lower().startswith("http") else "https://" + url

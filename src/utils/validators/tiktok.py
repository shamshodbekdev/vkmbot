import re
from typing import Optional

TIKTOK_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.|vm\.|vt\.)?tiktok\.com/"
    r"(?:"
    r"@[\w.]+/video/\d+"
    r"|v/\d+"
    r"|t/[\w]+"
    r"|\w+/?$"
    r")",
    re.IGNORECASE,
)


def extract_tiktok_url(text: str) -> Optional[str]:
    match = TIKTOK_PATTERN.search(text)
    if not match:
        return None
    return match.group(0)

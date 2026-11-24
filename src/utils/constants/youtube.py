from typing import List

YOUTUBE_PAGE_SIZE: int = 10
MAX_RESULTS_CYCLE: List[int] = [6, 8, 10, 12]
MOOD_PLAYLIST_PAGE_SIZE: int = 8
CHARTS_COUNTRY_WINDOW_SIZE: int = 5
MOOD_PAGE_SIZE: int = 10

# Search queries are stored in Redis and referenced from buttons by a short token.
MAX_QUERY_LENGTH: int = 256
QUERY_TTL: int = 7 * 24 * 3600

# Telegram limits audio title/performer metadata; the DB columns are 255 chars.
MAX_AUDIO_META_LENGTH: int = 255

# /new: YouTube Music's daily chart ("Daily Top Music Videos"). Uzbekistan has no
# chart of its own on YouTube Music; Russia's is the closest to what Uzbek
# listeners know (Russian and Uzbek hits).
NEW_SONGS_COUNTRY: str = "RU"
NEW_SONGS_PAGE_SIZE: int = 10
NEW_SONGS_LIMIT: int = 100
NEW_SONG_VERSIONS: int = 5

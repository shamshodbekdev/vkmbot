"""Data for /new: the daily "new popular songs" chart and the versions of one song."""
import re
from typing import List, Optional

from schemas.playlist import PlaylistSchema, PlaylistTrackSchema
from schemas.youtube_search import SongSchema
from services.youtube.charts import YouTubeCharts
from services.youtube.playlist import YouTubePlaylist
from services.youtube.search import YouTubeSearch
from utils.constants.youtube import NEW_SONG_VERSIONS, NEW_SONGS_COUNTRY, NEW_SONGS_LIMIT

# "(Official Video)", "[Official Music Video]", "| Official Audio", "(Lyric Video)", "(MV)" ...
_NOISE = re.compile(
    r"\s*[\(\[\|][^\)\]\|]*\b(official|video|audio|lyrics?|clip|klip|mv|m/v|visuali[sz]er|премьера|клип)\b[^\)\]]*[\)\]]?",
    re.IGNORECASE,
)


def clean_title(title: str) -> str:
    cleaned = _NOISE.sub("", title or "").strip(" -–—|")
    return cleaned or (title or "").strip()


# Channel-name suffixes that are not part of the artist's name.
_CHANNEL_NOISE = re.compile(r"\s*(\(official\)|official|vevo|- topic)\s*$", re.IGNORECASE)


def clean_artist(name: str) -> str:
    cleaned = _CHANNEL_NOISE.sub("", name or "").strip()
    return cleaned or (name or "").strip()


def track_label(track: PlaylistTrackSchema) -> str:
    """ "Artist — Title" without the "(Official Video)" noise; artist not repeated."""
    title = clean_title(track.title)
    artist = ", ".join(clean_artist(a.name) for a in track.artists if a.name)
    if artist and not title.lower().startswith(artist.lower()):
        return "%s — %s" % (artist, title)
    return title


class NewSongs:
    @staticmethod
    async def playlist(country: str = NEW_SONGS_COUNTRY) -> Optional[PlaylistSchema]:
        """The daily chart playlist (cached in Redis by the YouTube API layer)."""
        charts = await YouTubeCharts.get(country=country)
        if not charts or not charts.videos:
            return None
        daily = next((v for v in charts.videos if v.title.lower().startswith("daily") and v.playlistId), None)
        chosen = daily or next((v for v in charts.videos if v.playlistId), None)
        if not chosen:
            return None
        return await YouTubePlaylist.get(playlist_id=chosen.playlistId, limit=NEW_SONGS_LIMIT)

    @classmethod
    async def tracks(cls) -> List[PlaylistTrackSchema]:
        playlist = await cls.playlist()
        return [t for t in (playlist.tracks if playlist else []) if t.videoId and t.isAvailable]

    @staticmethod
    async def versions(track: PlaylistTrackSchema) -> List[SongSchema]:
        """Up to NEW_SONG_VERSIONS song versions of a chart track, found by search."""
        query = track_label(track).replace(" — ", " ")
        songs = await YouTubeSearch.search(query=query, limit=NEW_SONG_VERSIONS, fallback=True)
        return [s for s in songs if s.videoId][:NEW_SONG_VERSIONS]

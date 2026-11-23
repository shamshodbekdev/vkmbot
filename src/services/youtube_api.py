"""Free, local YouTube / YouTube Music API.

* Metadata (search, suggestions, songs, playlists, charts, moods): ``ytmusicapi``.
  The schemas in ``schemas/`` were written against ytmusicapi's output, so the
  results are validated with them unchanged.
* Audio / video files: ``yt-dlp`` + ffmpeg, downloaded to a temp directory.
"""
import asyncio
import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel
from ytmusicapi import YTMusic

from schemas.charts import ChartsSchema
from schemas.mood import MoodItemSchema, MoodPlaylistItemSchema
from schemas.playlist import PlaylistSchema, PlaylistTrackSchema
from schemas.song_detail import SongDetailSchema
from schemas.youtube_download import SongDownloadSchema
from schemas.youtube_search import SongSchema
from services.media_downloader import (
    MAX_UPLOAD_BYTES,
    base_options,
    downloaded_path,
    extract,
    fits_upload_limit,
    new_job_dir,
)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

AUDIO_BITRATE_KBPS: int = 128
# Longest track that still fits the upload limit at AUDIO_BITRATE_KBPS (with ~5% headroom).
MAX_AUDIO_SECONDS: int = int(MAX_UPLOAD_BYTES * 8 / (AUDIO_BITRATE_KBPS * 1000) * 0.95)

_local = threading.local()


def _client() -> YTMusic:
    """One YTMusic client per worker thread (its requests.Session is not thread-safe)."""
    client = getattr(_local, "client", None)
    if client is None:
        client = _local.client = YTMusic()
    return client


def _drop_none(value: Any) -> Any:
    """ytmusicapi uses None for missing fields; the schemas expect the key to be absent."""
    if isinstance(value, dict):
        return {k: _drop_none(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [_drop_none(v) for v in value if v is not None]
    return value


def _validate(schema: Type[T], raw: Any) -> Optional[T]:
    try:
        return schema.model_validate(_drop_none(raw))
    except Exception as error:
        logger.debug("Skipping item that does not match %s: %r", schema.__name__, error)
        return None


def _validate_list(schema: Type[T], raw: Any) -> List[T]:
    items = raw if isinstance(raw, list) else []
    return [item for item in (_validate(schema, i) for i in items) if item is not None]


async def _call(name: str, fn: Callable[[], Any], default: Any) -> Any:
    try:
        return await asyncio.to_thread(fn)
    except Exception as error:
        logger.warning("ytmusicapi %s failed: %r", name, error)
        return default


@dataclass
class MediaFile:
    path: Path
    title: str
    duration: float
    filesize: int


class YouTubeAPI:
    # ---- metadata (ytmusicapi) -------------------------------------------------

    @classmethod
    async def search(cls, query: str, limit: int, offset: int = 0, fallback: bool = False) -> List[SongSchema]:
        """Search YouTube Music songs.

        ``fallback=True``: if the "songs" filter finds nothing (typical for long
        lyric phrases), retry without the filter and keep songs and videos only.
        """
        # ytmusicapi has no offset: fetch enough results and slice.
        raw = await _call(
            "search",
            lambda: _client().search(query, filter="songs", limit=offset + limit, ignore_spelling=True),
            [],
        )
        if not raw and fallback:
            raw = await _call(
                "search (unfiltered)",
                lambda: _client().search(query, limit=offset + limit, ignore_spelling=True),
                [],
            )
            raw = [r for r in raw if r.get("resultType") in ("song", "video") and r.get("videoId")]
        return await asyncio.to_thread(_validate_list, SongSchema, raw[offset:offset + limit])

    @classmethod
    async def suggestions(cls, query: str) -> List[str]:
        raw = await _call("suggestions", lambda: _client().get_search_suggestions(query, detailed_runs=False), [])
        return [s for s in raw if isinstance(s, str)]

    @classmethod
    async def song(cls, video_id: str) -> Optional[SongDetailSchema]:
        raw = await _call("get_song", lambda: _client().get_song(video_id), None)
        return _validate(SongDetailSchema, raw) if raw else None

    @classmethod
    async def playlist(
        cls,
        playlist_id: str,
        limit: int = 100,
        related: bool = False,
        suggestions_limit: int = 0,
    ) -> Optional[PlaylistSchema]:
        raw = await _call(
            "get_playlist",
            lambda: _client().get_playlist(
                playlist_id, limit=limit, related=related, suggestions_limit=suggestions_limit
            ),
            None,
        )
        if not raw:
            return None
        # Validate tracks one by one so a single odd track cannot hide the whole playlist.
        tracks = _validate_list(PlaylistTrackSchema, raw.pop("tracks", None) or [])
        playlist = _validate(PlaylistSchema, raw)
        if playlist:
            playlist.tracks = tracks
        return playlist

    @classmethod
    async def charts(cls, country: str = "ZZ") -> Optional[ChartsSchema]:
        raw = await _call("get_charts", lambda: _client().get_charts(country=country), None)
        return _validate(ChartsSchema, raw) if raw else None

    @classmethod
    async def moods(cls) -> Dict[str, List[MoodItemSchema]]:
        raw = await _call("get_mood_categories", lambda: _client().get_mood_categories(), {})
        return {category: _validate_list(MoodItemSchema, items) for category, items in raw.items()}

    @classmethod
    async def mood_playlists(cls, params: str) -> List[MoodPlaylistItemSchema]:
        raw = await _call("get_mood_playlists", lambda: _client().get_mood_playlists(params), [])
        return _validate_list(MoodPlaylistItemSchema, raw)

    # ---- files (yt-dlp) --------------------------------------------------------

    @classmethod
    async def download_audio(cls, video_id: str) -> Optional[MediaFile]:
        """Download a track as MP3. Returns None if it is unavailable or too long."""
        job_dir = new_job_dir()
        options = base_options(job_dir, "youtube")
        options.update(
            format="bestaudio[ext=m4a]/bestaudio/best",
            match_filter=lambda info, *_: (
                "too long for Telegram" if (info.get("duration") or 0) > MAX_AUDIO_SECONDS else None
            ),
            postprocessors=[dict(
                key="FFmpegExtractAudio",
                preferredcodec="mp3",
                preferredquality=str(AUDIO_BITRATE_KBPS),
            )],
        )
        info = await extract("https://www.youtube.com/watch?v=%s" % video_id, options, download=True)
        if not info:
            return None
        path = downloaded_path(info)
        if not path or path.suffix != ".mp3":
            mp3s = list(job_dir.glob("*.mp3"))
            path = mp3s[0] if mp3s else None
        if not path:
            logger.warning("YouTube %s: no audio produced (duration %s s)", video_id, info.get("duration"))
            return None
        if not fits_upload_limit(path):
            return None
        return MediaFile(
            path=path,
            title=info.get("title") or "",
            duration=float(info.get("duration") or 0),
            filesize=path.stat().st_size,
        )

    @classmethod
    async def download_video(cls, url: str) -> Optional[MediaFile]:
        """Download a YouTube video / Short as MP4 (H.264, at most 720p) that fits the upload limit."""
        job_dir = new_job_dir()
        options = base_options(job_dir, "youtube")
        limit_mb = MAX_UPLOAD_BYTES // (1024 * 1024)
        options.update(
            format=(
                "bv*[height<=720][vcodec^=avc][filesize<{0}M]+ba[ext=m4a]"
                "/b[height<=720][ext=mp4][filesize<{0}M]"
                "/bv*[height<=480][vcodec^=avc]+ba[ext=m4a]"
                "/b[height<=480]/b"
            ).format(limit_mb),
            merge_output_format="mp4",
        )
        info = await extract(url, options, download=True)
        if not info:
            return None
        path = downloaded_path(info)
        if not path or not fits_upload_limit(path):
            return None
        return MediaFile(
            path=path,
            title=info.get("title") or "",
            duration=float(info.get("duration") or 0),
            filesize=path.stat().st_size,
        )

    @classmethod
    async def download(cls, video_id: str) -> Optional[SongDownloadSchema]:
        """Same shape the old remote ``/download`` endpoint returned; ``link`` is a local path."""
        audio = await cls.download_audio(video_id)
        if not audio:
            return None
        return SongDownloadSchema(
            progress=100,
            title=audio.title,
            duration=audio.duration,
            filesize=audio.filesize,
            link=str(audio.path),
        )

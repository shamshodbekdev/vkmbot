"""Free, local YouTube / YouTube Music API.

* Metadata (search, suggestions, songs, playlists, charts, moods): ``ytmusicapi``.
  The schemas in ``schemas/`` were written against ytmusicapi's output, so the
  results are validated with them unchanged.
* Audio / video files: ``yt-dlp`` + ffmpeg, downloaded to a temp directory.
"""
import asyncio
import hashlib
import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar

import aiohttp
from pydantic import BaseModel
from ytmusicapi import YTMusic

from core.cache import cache
from schemas.charts import ChartsSchema
from schemas.mood import MoodItemSchema, MoodPlaylistItemSchema
from schemas.playlist import PlaylistSchema, PlaylistTrackSchema
from schemas.song_detail import SongDetailSchema
from schemas.youtube_download import SongDownloadSchema
from schemas.youtube_search import SongSchema
from services.media_downloader import (
    MAX_UPLOAD_BYTES,
    MEDIA_TMP_DIR,
    FileTooLargeError,
    ParallelDownloadError,
    base_options,
    download_parallel,
    progress_tracker,
    selected_size,
    discard_dir,
    download_url,
    downloaded_path,
    extract,
    STANDARD_QUALITIES,
    codec_score,
    fits_upload_limit,
    http_session,
    quality_of,
    is_too_large,
    new_job_dir,
    run_ffmpeg,
    size_aware_format,
)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# Redis cache lifetimes for YouTube Music metadata (seconds).
SEARCH_TTL: int = 30 * 60
SEARCH_BLOCK: int = 40
SONG_TTL: int = 24 * 60 * 60
PLAYLIST_TTL: int = 30 * 60
CHARTS_TTL: int = 60 * 60
MOODS_TTL: int = 6 * 60 * 60

AUDIO_BITRATE_KBPS: int = 128
# Longest track that still fits the upload limit at AUDIO_BITRATE_KBPS (with ~5% headroom).
# Music stays capped at the cloud limit (50 MB, ~52 min) even with a local Bot API
# server: hour-long "songs" would only waste disk and the users' traffic.
MUSIC_MAX_BYTES: int = min(MAX_UPLOAD_BYTES, 50 * 1024 * 1024)
MAX_AUDIO_SECONDS: int = int(MUSIC_MAX_BYTES * 8 / (AUDIO_BITRATE_KBPS * 1000) * 0.95)

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


async def _call(name: str, fn: Callable[[], Any], default: Any, cache_key: Optional[str] = None, ttl: int = 0) -> Any:
    """Run a ytmusicapi call in a worker thread, with an optional Redis cache.

    Only non-empty results are cached, so a temporary failure is never remembered.
    """
    key = None
    if cache_key and ttl:
        key = "ytm:%s:%s" % (name, hashlib.sha1(cache_key.encode("utf-8")).hexdigest())
        try:
            cached = await cache.get(key)
            if cached is not None:
                return cached
        except Exception as error:
            logger.debug("cache read failed for %s: %r", key, error)
    try:
        result = await asyncio.to_thread(fn)
    except Exception as error:
        logger.warning("ytmusicapi %s failed: %r", name, error)
        return default
    if key and result:
        try:
            await cache.set(key, result, ttl=ttl)
        except Exception as error:
            logger.debug("cache write failed for %s: %r", key, error)
    return result


@dataclass
class MediaFile:
    path: Path
    title: str
    duration: float
    filesize: int
    width: Optional[int] = None
    height: Optional[int] = None


@dataclass
class VideoInfo:
    video_id: str
    title: str
    duration: int
    uploader: str
    thumbnail_url: str
    # Resolution ("720") -> smallest size in bytes a video of that resolution can
    # be sent at (0 = unknown). Only resolutions the video really has are listed.
    qualities: Dict[str, int] = field(default_factory=dict)


def available_qualities(raw: Dict[str, Any]) -> Dict[str, int]:
    """Standard resolutions a YouTube video offers, with the smallest MP4 size for each."""
    formats = [f for f in raw.get("formats") or [] if f.get("vcodec") not in (None, "none") and f.get("ext") != "mhtml"]
    duration = float(raw.get("duration") or 0)

    def size(f: Dict[str, Any]) -> int:
        known = f.get("filesize") or f.get("filesize_approx")
        if known:
            return int(known)
        return int(f["tbr"] * 1000 / 8 * duration) if f.get("tbr") and duration else 0

    audio = [f for f in raw.get("formats") or [] if f.get("vcodec") == "none" and f.get("acodec") not in (None, "none")]
    m4a = [size(f) for f in audio if f.get("ext") == "m4a" and size(f)]
    audio_size = max(m4a) if m4a else 0

    sizes: Dict[int, List[tuple]] = {}
    for f in formats:
        quality = quality_of(f)
        if not quality:
            continue
        total = size(f)
        if total and f.get("acodec") in (None, "none"):
            total += audio_size  # video-only stream: the audio track is merged in
        sizes.setdefault(quality, []).append((codec_score(f) > 0, total))
    found: Dict[int, int] = {}
    for quality, options in sizes.items():
        # Prefer H.264/VP9 sizes (what would be sent); AV1 only if nothing else exists.
        preferred = [t for ok, t in options if ok] or [t for _ok, t in options]
        known = [t for t in preferred if t]
        found[quality] = min(known) if known else 0
    offered = {q: found[q] for q in STANDARD_QUALITIES if q in found}
    if not offered and found:
        # Very old / low-res uploads: still offer their best resolution.
        top = max(found)
        offered = {top: found[top]}
    return {str(q): size_ for q, size_ in offered.items()}


def _info_key(url: str) -> str:
    # v2: entries carry the available resolutions.
    return "ytinfo2:%s" % hashlib.sha1(url.encode("utf-8")).hexdigest()


def fallback_thumbnail(video_id: str) -> str:
    """hqdefault.jpg exists for every public video (maxresdefault does not)."""
    return "https://i.ytimg.com/vi/%s/hqdefault.jpg" % video_id


def watch_url(video_id: str) -> str:
    return "https://www.youtube.com/watch?v=%s" % video_id


def jpeg_thumbnails(info: Dict[str, Any]) -> List[str]:
    """JPEG thumbnail URLs, best first (Telegram photos do not reliably accept WebP).

    yt-dlp lists YouTube's named thumbnails without checking them and often
    without sizes, so they are ranked by name; callers must verify the URL exists.
    """
    names = ("mqdefault", "hqdefault", "sddefault", "hq720", "maxresdefault")

    def rank(t: Dict[str, Any]):
        path = t["url"].split("?")[0]
        named = max((i + 1 for i, n in enumerate(names) if path.endswith("/%s.jpg" % n)), default=0)
        return named, (t.get("width") or 0) * (t.get("height") or 0), t.get("preference") or 0

    candidates = [t for t in (info.get("thumbnails") or []) if t.get("url") and ".jpg" in t["url"].split("?")[0]]
    urls = [t["url"] for t in sorted(candidates, key=rank, reverse=True)]
    return list(dict.fromkeys(urls + [fallback_thumbnail(info.get("id") or "")]))


async def first_reachable(urls: List[str]) -> Optional[str]:
    timeout = aiohttp.ClientTimeout(total=5)
    session = http_session()
    for url in urls[:6]:
        try:
            async with session.head(url, allow_redirects=True, timeout=timeout) as response:
                if response.status == 200:
                    return url
        except Exception as error:
            logger.debug("thumbnail check failed for %s: %r", url, error)
    return None


class YouTubeAPI:
    # ---- metadata (ytmusicapi) -------------------------------------------------

    @classmethod
    async def search(cls, query: str, limit: int, offset: int = 0, fallback: bool = False) -> List[SongSchema]:
        """Search YouTube Music songs.

        ``fallback=True``: if the "songs" filter finds nothing (typical for long
        lyric phrases), retry without the filter and keep songs and videos only.
        """
        # ytmusicapi has no offset: fetch enough results and slice. Results are
        # fetched in blocks of SEARCH_BLOCK (one request returns that many anyway),
        # so every page size setting and the first pages share one cache entry.
        query = " ".join(query.split())
        wanted = -(-(offset + limit) // SEARCH_BLOCK) * SEARCH_BLOCK
        key = "%s|%d" % (query.lower(), wanted)
        raw = await _call(
            "search",
            lambda: _client().search(query, filter="songs", limit=wanted, ignore_spelling=True),
            [],
            cache_key=key,
            ttl=SEARCH_TTL,
        )
        if not raw and fallback:
            raw = await _call(
                "search (unfiltered)",
                lambda: _client().search(query, limit=wanted, ignore_spelling=True),
                [],
                cache_key=key,
                ttl=SEARCH_TTL,
            )
            raw = [r for r in raw if r.get("resultType") in ("song", "video") and r.get("videoId")]
        # A handful of items: validating inline is faster than a thread hop.
        return _validate_list(SongSchema, raw[offset:offset + limit])

    @classmethod
    async def suggestions(cls, query: str) -> List[str]:
        raw = await _call(
            "suggestions", lambda: _client().get_search_suggestions(query, detailed_runs=False), [],
            cache_key=query.lower(), ttl=SEARCH_TTL,
        )
        return [s for s in raw if isinstance(s, str)]

    @classmethod
    async def song(cls, video_id: str) -> Optional[SongDetailSchema]:
        raw = await _call("get_song", lambda: _client().get_song(video_id), None, cache_key=video_id, ttl=SONG_TTL)
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
            cache_key="%s|%s|%s|%s" % (playlist_id, limit, related, suggestions_limit),
            ttl=PLAYLIST_TTL,
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
        raw = await _call("get_charts", lambda: _client().get_charts(country=country), None, cache_key=country, ttl=CHARTS_TTL)
        return _validate(ChartsSchema, raw) if raw else None

    @classmethod
    async def moods(cls) -> Dict[str, List[MoodItemSchema]]:
        raw = await _call("get_mood_categories", lambda: _client().get_mood_categories(), {}, cache_key="all", ttl=MOODS_TTL)
        return {category: _validate_list(MoodItemSchema, items) for category, items in raw.items()}

    @classmethod
    async def mood_playlists(cls, params: str) -> List[MoodPlaylistItemSchema]:
        raw = await _call(
            "get_mood_playlists", lambda: _client().get_mood_playlists(params), [], cache_key=params, ttl=MOODS_TTL,
        )
        return _validate_list(MoodPlaylistItemSchema, raw)

    # ---- files (yt-dlp) --------------------------------------------------------

    @classmethod
    async def download_audio(cls, video_id: str) -> Optional[MediaFile]:
        """Download a track as M4A (AAC). Returns None if it is unavailable or too long.

        YouTube already serves AAC audio, so the stream is copied into an .m4a
        container without re-encoding (~4x faster than converting to MP3).
        Other codecs (rare) are converted to AAC by ffmpeg.
        """
        job_dir = new_job_dir()
        options = base_options(job_dir, "youtube")
        options.update(
            format="bestaudio[ext=m4a]/bestaudio/best",
            match_filter=lambda info, *_: (
                "too long for Telegram" if (info.get("duration") or 0) > MAX_AUDIO_SECONDS else None
            ),
            postprocessors=[dict(
                key="FFmpegExtractAudio",
                preferredcodec="m4a",
                preferredquality=str(AUDIO_BITRATE_KBPS),
            )],
        )
        info = await extract("https://www.youtube.com/watch?v=%s" % video_id, options, download=True)
        if not info:
            discard_dir(job_dir)
            return None
        path = downloaded_path(info)
        if not path or path.suffix != ".m4a":
            files = list(job_dir.glob("*.m4a"))
            path = files[0] if files else None
        if not path:
            logger.warning("YouTube %s: no audio produced (duration %s s)", video_id, info.get("duration"))
            discard_dir(job_dir)
            return None
        if not fits_upload_limit(path):
            discard_dir(job_dir)
            return None
        return MediaFile(
            path=path,
            title=info.get("title") or "",
            duration=float(info.get("duration") or 0),
            filesize=path.stat().st_size,
        )

    @classmethod
    async def _download_video_fast(cls, url: str, options: Dict[str, Any], job_dir: Path) -> Optional[MediaFile]:
        """Pick the version with yt-dlp, then fetch it over parallel connections.

        Several times faster than yt-dlp's single connection (which YouTube
        throttles). Returns None to let yt-dlp download it the usual way.
        Raises FileTooLargeError when even the chosen version is too large.
        """
        info = await extract(url, dict(options), download=False)
        if not info:
            return None
        size = selected_size(info)
        parts = info.get("requested_formats") or [info]
        logger.info(
            "YouTube %s: format %s (%s, %sx%s, %s), %.1f MB",
            info.get("id"), info.get("format_id"), info.get("vcodec"), info.get("width"), info.get("height"),
            info.get("dynamic_range") or "SDR", size / 1e6,
        )
        if size > MAX_UPLOAD_BYTES:
            raise FileTooLargeError(url)
        try:
            path = await download_parallel(info, job_dir, str(info.get("id") or "video"), progress_tracker.get())
        except FileTooLargeError:
            raise
        except (ParallelDownloadError, OSError, aiohttp.ClientError, asyncio.TimeoutError) as error:
            logger.warning("Parallel download of %s failed, using yt-dlp instead: %r", url, error)
            return None
        if path is None:
            logger.info("Parallel download not possible for %s (%s), using yt-dlp",
                        url, "+".join(str(p.get("protocol")) for p in parts))
            return None
        return MediaFile(
            path=path,
            title=info.get("title") or "",
            duration=float(info.get("duration") or 0),
            filesize=path.stat().st_size,
            width=info.get("width"),
            height=info.get("height"),
        )

    @classmethod
    async def download_video(cls, url: str, quality: Optional[int] = None) -> Optional[MediaFile]:
        """Download a YouTube video / Short as MP4 that fits the upload limit.

        ``quality`` (e.g. 720) asks for exactly that resolution; without it the best
        version up to 720p is chosen. Raises FileTooLargeError when it cannot fit.
        """
        job_dir = new_job_dir()
        options = base_options(job_dir, "youtube")
        options.update(
            # Best H.264 version up to 720p whose real size fits the upload limit
            # (falls back to 480p / 360p for long videos).
            format=size_aware_format(resolution=quality) if quality else size_aware_format(max_short_side=720),
            merge_output_format="mp4",
        )
        fast = await cls._download_video_fast(url, options, job_dir)
        if fast is not None:
            return fast
        tracker = progress_tracker.get()
        if tracker is not None:
            tracker.parts.clear()
        info = await extract(url, options, download=True)
        path = downloaded_path(info) if info else None
        if not path or not fits_upload_limit(path):
            discard_dir(job_dir)
            if is_too_large(info) or path:
                raise FileTooLargeError(url)
            return None
        return MediaFile(
            path=path,
            title=info.get("title") or "",
            duration=float(info.get("duration") or 0),
            filesize=path.stat().st_size,
            width=info.get("width"),
            height=info.get("height"),
        )

    @classmethod
    async def info(cls, url: str) -> Optional[VideoInfo]:
        """Title, duration and thumbnail of a video without downloading it (cached in Redis)."""
        key = _info_key(url)
        try:
            cached = await cache.get(key)
            if cached:
                return VideoInfo(**cached)
        except Exception as error:
            logger.debug("cache read failed for %s: %r", key, error)

        MEDIA_TMP_DIR.mkdir(parents=True, exist_ok=True)
        options = base_options(MEDIA_TMP_DIR, "youtube")
        # Metadata only: never fail because of format selection.
        options.update(format="bestaudio/best", ignore_no_formats_error=True)
        raw = await extract(url, options, download=False)
        # With ignore_no_formats_error yt-dlp returns a placeholder for deleted /
        # unavailable videos: a real, downloadable video always has formats.
        if not raw or not raw.get("id") or not raw.get("formats"):
            logger.warning("YouTube video unavailable: %s", url)
            return None
        info = VideoInfo(
            video_id=raw["id"],
            title=raw.get("title") or "YouTube",
            duration=int(raw.get("duration") or 0),
            uploader=raw.get("uploader") or raw.get("channel") or "",
            thumbnail_url=await first_reachable(jpeg_thumbnails(raw)) or fallback_thumbnail(raw["id"]),
            qualities=available_qualities(raw),
        )
        try:
            await cache.set(key, info.__dict__, ttl=SONG_TTL)
            # Also under the canonical link, so buttons can find it by video id.
            await cache.set(_info_key(watch_url(info.video_id)), info.__dict__, ttl=SONG_TTL)
        except Exception as error:
            logger.debug("cache write failed for %s: %r", key, error)
        return info

    @classmethod
    async def cached_info(cls, video_id: str) -> Optional[VideoInfo]:
        """The preview's info for ``video_id`` if still cached (never hits YouTube)."""
        try:
            cached = await cache.get(_info_key(watch_url(video_id)))
            return VideoInfo(**cached) if cached else None
        except Exception as error:
            logger.debug("cached info read failed for %s: %r", video_id, error)
            return None

    @classmethod
    async def thumbnail_file(cls, video_id: str, thumbnail_url: Optional[str] = None) -> Optional[Path]:
        """JPEG preview for a video/audio upload: max 320 px and < 200 kB, as Telegram requires."""
        job_dir = new_job_dir()
        source = await download_url(
            thumbnail_url or "https://i.ytimg.com/vi/%s/hqdefault.jpg" % video_id, job_dir / "source.jpg",
            queue=False,
        )
        if not source:
            discard_dir(job_dir)
            return None
        thumb = job_dir / "thumb.jpg"
        result = await run_ffmpeg(
            "-y", "-i", str(source), "-vf", "scale=320:320:force_original_aspect_ratio=decrease",
            "-q:v", "4", str(thumb),
        )
        if result is None or not thumb.is_file() or thumb.stat().st_size >= 200 * 1024:
            discard_dir(job_dir)
            return None
        return thumb

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

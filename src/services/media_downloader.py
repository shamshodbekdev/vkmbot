"""Shared helpers for the local, free media modules (yt-dlp + ffmpeg).

Everything here runs on this server: no third-party API is involved.
Blocking work (yt-dlp, ffmpeg) is pushed to worker threads so the bot's
event loop never stalls. Two limits protect the server:

* a global semaphore caps how many downloads run at once (extra requests wait
  in a queue and the user is told so), and
* :func:`user_download_slot` caps simultaneous downloads per user.

yt-dlp runs in dedicated thread pools (downloads / metadata), so busy downloads
can never starve the default pool that searches and other work use.

Transient platform errors (YouTube's "confirm you're not a bot" rate limit,
HTTP 429/5xx, timeouts) are retried with a short backoff.
"""
import asyncio
import contextvars
import datetime
import json
import logging
import urllib.request
import os
import re
import shutil
import tempfile
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Any, AsyncIterator, Awaitable, Callable, Dict, Iterator, List, Optional, Sequence, Union

import aiofiles
import aiohttp
import yt_dlp
from aiogram.types import FSInputFile, InputFile, URLInputFile

from core.config import BASE_DIR, config

logger = logging.getLogger(__name__)

MEDIA_TMP_DIR: Path = Path(tempfile.gettempdir()) / "vkm-bot-media"
# Optional Netscape-format cookie files. When present they are passed to yt-dlp,
# which lets it fetch posts that the platform only shows to logged-in users.
COOKIES_DIR: Path = BASE_DIR / "cookies"

# Bot API upload limit: 50 MB on api.telegram.org, 2000 MB on a local Bot API server.
MAX_UPLOAD_BYTES: int = (2000 if config.telegram_api_local else 50) * 1024 * 1024
MAX_UPLOAD_MB: int = MAX_UPLOAD_BYTES // (1024 * 1024)
# getFile limit: a bot can only download files up to 20 MB from api.telegram.org.
MAX_TELEGRAM_DOWNLOAD_BYTES: int = (2000 if config.telegram_api_local else 20) * 1024 * 1024
MAX_PARALLEL_DOWNLOADS: int = 20
MAX_DOWNLOADS_PER_USER: int = 5
METADATA_THREADS: int = 8
DEFAULT_THREADS: int = 32
TMP_MAX_AGE_SECONDS: int = 60 * 60
PURGE_INTERVAL_SECONDS: int = 5 * 60

# Delays before the 2nd and 3rd attempt when a platform error looks transient.
RETRY_DELAYS: Sequence[float] = (3.0, 8.0)
_RETRYABLE = re.compile(
    r"confirm you.re not a bot|HTTP Error (429|5\d\d)|timed? ?out|Connection (reset|aborted|refused)"
    r"|Remote end closed|IncompleteRead|Temporary failure|rate.?limit|try again later"
    # YouTube sometimes answers 403 for a stream URL; a fresh extraction usually works.
    r"|unable to download video data: HTTP Error 403",
    re.IGNORECASE,
)

BROWSER_HEADERS: Dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

_semaphore = asyncio.Semaphore(MAX_PARALLEL_DOWNLOADS)
_waiting: int = 0
_running: int = 0
_ffmpeg_slots = asyncio.Semaphore(os.cpu_count() or 4)
_user_active: Dict[int, int] = defaultdict(int)
_last_purge: float = 0.0

_download_pool = ThreadPoolExecutor(max_workers=MAX_PARALLEL_DOWNLOADS, thread_name_prefix="yt-dlp-download")
_metadata_pool = ThreadPoolExecutor(max_workers=METADATA_THREADS, thread_name_prefix="yt-dlp-info")
_http: Optional[aiohttp.ClientSession] = None

# Set per update by DownloadLimitMiddleware: called when a download has to wait
# for a free slot; returns a message to delete once the download starts.
queue_notifier: contextvars.ContextVar[Optional[Callable[[], Awaitable[Any]]]] = contextvars.ContextVar(
    "queue_notifier", default=None,
)


class DownloadProgress:
    """Bytes fetched so far for one request; read by the "⏳ Downloading... X%" message."""

    def __init__(self) -> None:
        self.total: int = 0
        self.parts: Dict[str, int] = {}

    @property
    def done(self) -> int:
        return sum(self.parts.values())

    def update(self, part: str, done: int) -> None:
        self.parts[part] = done

    @property
    def percent(self) -> Optional[int]:
        if not self.total:
            return None
        return max(0, min(99, self.done * 100 // self.total))


# Set by a handler that shows download progress; the download layer fills it in.
progress_tracker: contextvars.ContextVar[Optional[DownloadProgress]] = contextvars.ContextVar(
    "progress_tracker", default=None,
)


class FileTooLargeError(Exception):
    """The media exists but even its smallest version is above the Telegram upload limit."""


def configure_executors() -> None:
    """Give asyncio.to_thread (searches, charts, transcription...) a roomier default pool.

    Python's default is min(32, cores + 4) = 8 threads here, which a few slow
    jobs could fill. Call once from on_startup, inside the running loop.
    """
    asyncio.get_running_loop().set_default_executor(
        ThreadPoolExecutor(max_workers=DEFAULT_THREADS, thread_name_prefix="worker"),
    )


def shutdown_executors() -> None:
    """Drop queued downloads on shutdown. Running yt-dlp threads cannot be stopped;
    main.py exits without waiting for them (their temp folders are purged later)."""
    for pool in (_download_pool, _metadata_pool):
        pool.shutdown(wait=False, cancel_futures=True)


def http_session() -> aiohttp.ClientSession:
    """One shared, pooled aiohttp session (keep-alive: no TCP/TLS handshake per request)."""
    global _http
    if _http is None or _http.closed:
        _http = aiohttp.ClientSession(
            headers=BROWSER_HEADERS,
            connector=aiohttp.TCPConnector(limit=100, limit_per_host=20, ttl_dns_cache=300),
        )
    return _http


async def close_http_session() -> None:
    global _http
    if _http is not None and not _http.closed:
        await _http.close()
    _http = None


@asynccontextmanager
async def download_slot() -> AsyncIterator[None]:
    """Global download slot; when all are busy the request queues and the user is told."""
    global _waiting, _running
    notice = None
    if _semaphore.locked():
        notify = queue_notifier.get()
        if notify is not None:
            queue_notifier.set(None)  # tell each request only once
            with suppress(Exception):
                notice = await notify()
        _waiting += 1
        try:
            await _semaphore.acquire()
        finally:
            _waiting -= 1
            if notice is not None:
                with suppress(Exception):
                    await notice.delete()
    else:
        await _semaphore.acquire()
    _running += 1
    try:
        yield
    finally:
        _running -= 1
        _semaphore.release()


@asynccontextmanager
async def _no_slot() -> AsyncIterator[None]:
    yield


def load_status() -> Dict[str, int]:
    """Running / queued downloads (for the admin "System" screen and tests)."""
    return dict(running=_running, queued=_waiting, users=len(_user_active))


def _purge_old_dirs() -> None:
    """Remove job directories left behind by earlier downloads."""
    if not MEDIA_TMP_DIR.exists():
        return
    deadline = time.time() - TMP_MAX_AGE_SECONDS
    for entry in MEDIA_TMP_DIR.iterdir():
        try:
            if entry.stat().st_mtime < deadline:
                shutil.rmtree(entry, ignore_errors=True) if entry.is_dir() else entry.unlink()
        except OSError:
            pass


def new_job_dir() -> Path:
    """Create a fresh working directory for one download (stale ones are purged periodically)."""
    global _last_purge
    MEDIA_TMP_DIR.mkdir(parents=True, exist_ok=True)
    if time.time() - _last_purge > PURGE_INTERVAL_SECONDS:
        _last_purge = time.time()
        _purge_old_dirs()
    job_dir = Path(tempfile.mkdtemp(dir=MEDIA_TMP_DIR))
    if config.telegram_api_local:
        # The local Bot API server (another user, inside Docker) reads files from here.
        job_dir.chmod(0o755)
    return job_dir


@asynccontextmanager
async def user_download_slot(user_id: Optional[int]) -> AsyncIterator[bool]:
    """Yields False when ``user_id`` already has MAX_DOWNLOADS_PER_USER downloads running."""
    if user_id is None:
        yield True
        return
    if _user_active[user_id] >= MAX_DOWNLOADS_PER_USER:
        yield False
        return
    _user_active[user_id] += 1
    try:
        yield True
    finally:
        _user_active[user_id] -= 1
        if _user_active[user_id] <= 0:
            _user_active.pop(user_id, None)


def cookie_file(platform: str) -> Optional[str]:
    path = COOKIES_DIR / ("%s.txt" % platform)
    return str(path) if path.is_file() else None


def base_options(job_dir: Path, platform: str) -> Dict[str, Any]:
    options: Dict[str, Any] = dict(
        quiet=True,
        no_warnings=True,
        noprogress=True,
        noplaylist=True,
        restrictfilenames=True,
        socket_timeout=30,
        retries=3,
        paths=dict(home=str(job_dir), temp=str(job_dir)),
        outtmpl="%(id)s.%(ext)s",
        # Never fetch what Telegram would refuse: oversize files are skipped up front.
        max_filesize=MAX_UPLOAD_BYTES,
    )
    if platform == "youtube":
        # A stream YouTube slows to a crawl (< 100 KB/s) is dropped and fetched
        # again with fresh URLs instead of taking minutes.
        options["throttledratelimit"] = 100 * 1024
    cookies = cookie_file(platform)
    if cookies:
        options["cookiefile"] = cookies
    return options


_AVC = ("avc", "h264")
# Resolutions offered to users ("p" = the video's short side, as YouTube labels them).
STANDARD_QUALITIES: Sequence[int] = (360, 480, 720, 1080, 1440, 2160)
_QUALITY_NOTE = re.compile(r"^(\d{3,4})p")


def quality_of(fmt: Dict[str, Any]) -> int:
    """A format's resolution label as YouTube shows it, as a number (1080 for "1080p60")."""
    match = _QUALITY_NOTE.match(str(fmt.get("format_note") or ""))
    if match:
        return int(match.group(1))
    width, height = fmt.get("width") or 0, fmt.get("height") or 0
    if not (width and height):
        return height or width or 0
    # YouTube's rule (checked against its own labels): the standard 16:9 size with
    # the closest pixel count. So a vertical 608x1080 Short is "480p", 720x1280 is
    # "720p" and a cinema-wide 1920x800 film is "1080p".
    area = width * height
    return min((144, 240) + tuple(STANDARD_QUALITIES), key=lambda q: abs(q * q * 16 / 9 - area))


def codec_score(fmt: Dict[str, Any]) -> int:
    """H.264 plays on every Telegram client, VP9 on most, AV1 on few."""
    vcodec = str(fmt.get("vcodec") or "").lower()
    if vcodec.startswith(_AVC):
        return 2
    if vcodec.startswith(("vp9", "vp09")):
        return 1
    return 0


def _is_hls(fmt: Dict[str, Any]) -> bool:
    return "m3u8" in str(fmt.get("protocol") or "")


def _duration_hint(formats: List[Dict[str, Any]]) -> Optional[float]:
    """Media length worked out from any format whose size and bitrate are both known."""
    for f in formats:
        size, tbr = f.get("filesize") or f.get("filesize_approx"), f.get("tbr")
        if size and tbr:
            return size * 8 / (tbr * 1000)
    return None


def _remote_size(fmt: Dict[str, Any], duration: Optional[float] = None) -> Optional[int]:
    """Size of one format: known by yt-dlp, else estimated (bitrate x length), else
    asked with a HEAD request. Runs in a yt-dlp worker thread."""
    size = fmt.get("filesize") or fmt.get("filesize_approx")
    if size:
        return int(size)
    if duration and fmt.get("tbr"):
        # HLS streams have no size and cannot be stopped mid-way by max_filesize,
        # so never treat them as "unknown, maybe fits".
        return int(fmt["tbr"] * 1000 / 8 * duration * 1.05)
    url = fmt.get("url")
    if not url or not str(fmt.get("protocol") or "https").startswith("http") or _is_hls(fmt):
        return None
    try:
        request = urllib.request.Request(url, method="HEAD", headers=fmt.get("http_headers") or BROWSER_HEADERS)
        with urllib.request.urlopen(request, timeout=10) as response:
            length = response.headers.get("Content-Length")
            size = int(length) if length else None
    except Exception as error:
        logger.debug("HEAD %s failed: %r", url[:100], error)
        return None
    if size:
        fmt["filesize"] = size  # lets yt-dlp's max_filesize skip it without downloading
    return size


def size_aware_format(limit: int = int(MAX_UPLOAD_BYTES * 0.98), max_short_side: int = 1080,
                      exclude_note: Optional[str] = None,
                      resolution: Optional[int] = None) -> Callable[[Dict[str, Any]], Iterator[Dict[str, Any]]]:
    """yt-dlp ``format`` selector: the best version whose *real* size fits ``limit``.

    Platforms such as Instagram do not report sizes, so each candidate is checked
    with a HEAD request, best first: H.264 (plays on every Telegram client) before
    VP9/H.265, then higher resolution. With ``resolution`` only versions of exactly
    that resolution (see :func:`quality_of`) are considered. If nothing fits, the smallest version is
    returned with its size set, so ``max_filesize`` makes yt-dlp skip the download
    and the caller can tell the user the file is too large.
    """
    def short_side(f: Dict[str, Any]) -> int:
        w, h = f.get("width") or 0, f.get("height") or 0
        return min(w, h) if w and h else (h or w)

    def is_avc(f: Dict[str, Any]) -> bool:
        return str(f.get("vcodec") or "").lower().startswith(_AVC)

    def selector(ctx: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
        formats = [f for f in ctx.get("formats") or []
                   if not (exclude_note and exclude_note in str(f.get("format_note") or "").lower())]
        if not formats:
            formats = list(ctx.get("formats") or [])
        has_video = lambda f: f.get("vcodec") != "none" and f.get("ext") not in ("mhtml",)  # noqa: E731
        # Progressive = video+audio in one file; missing codec info (Instagram) counts too.
        progressive = [f for f in formats if has_video(f) and f.get("acodec") != "none"]
        video_only = [f for f in formats if has_video(f) and f.get("acodec") == "none"]
        audio = sorted(
            (f for f in formats if f.get("vcodec") == "none" and f.get("acodec") not in (None, "none")),
            key=lambda f: (f.get("ext") == "m4a", f.get("abr") or f.get("tbr") or 0),
            reverse=True,
        )

        candidates: List[Dict[str, Any]] = []
        seen = set()
        for f in progressive:
            if f.get("url") not in seen:
                seen.add(f.get("url"))
                candidates.append(f)
        if audio:
            best_audio = audio[0]
            for v in video_only:
                candidates.append(dict(
                    format_id="%s+%s" % (v["format_id"], best_audio["format_id"]),
                    ext="mp4",
                    requested_formats=[v, best_audio],
                    protocol="%s+%s" % (v.get("protocol"), best_audio.get("protocol")),
                    width=v.get("width"), height=v.get("height"),
                    vcodec=v.get("vcodec"), acodec=best_audio.get("acodec"),
                    tbr=v.get("tbr"), format_note=v.get("format_note"),
                    dynamic_range=v.get("dynamic_range"),
                ))

        if resolution:
            candidates = [c for c in candidates if quality_of(c) == resolution]
            if not candidates:
                return

        def rank(f: Dict[str, Any]):
            side = short_side(f)
            hls = _is_hls(f) or any(_is_hls(p) for p in f.get("requested_formats") or [])
            # HDR versions look washed out on most phones and are bigger: SDR first.
            sdr = str(f.get("dynamic_range") or "SDR").upper() == "SDR"
            if resolution:
                return (codec_score(f), sdr, not hls, f.get("tbr") or 0)
            return (side <= max_short_side, is_avc(f) and side >= 480, side, sdr, not hls, f.get("tbr") or 0)

        candidates.sort(key=rank, reverse=True)
        if not candidates:
            # Images or unusual entries: keep yt-dlp's own choice.
            if formats:
                yield formats[-1]
            return

        duration = _duration_hint(formats)

        def size_of(c: Dict[str, Any]) -> Optional[int]:
            if "requested_formats" not in c:
                return _remote_size(c, duration)
            parts = [_remote_size(part, duration) for part in c["requested_formats"]]
            known = sum(p for p in parts if p)
            if any(p is None for p in parts):
                # A known part alone may already exceed the limit: then it is too large.
                if known > limit:
                    c["filesize"] = known
                    return known
                return None
            c["filesize"] = sum(parts)
            return c["filesize"]

        unknown: Optional[Dict[str, Any]] = None  # size unknowable: plain HTTP only (max_filesize guards it)
        smallest: Optional[Dict[str, Any]] = None
        for c in candidates:
            if not resolution and short_side(c) > max_short_side and any(short_side(o) <= max_short_side for o in candidates):
                continue
            size = size_of(c)
            if size is None:
                hls = _is_hls(c) or any(_is_hls(p) for p in c.get("requested_formats") or [])
                if not hls:
                    unknown = unknown or c
                continue
            if size <= limit:
                yield c
                return
            if smallest is None or size < smallest["filesize"]:
                smallest = c
        if unknown is not None:
            yield unknown  # still guarded by max_filesize / fits_upload_limit
        elif smallest is not None:
            logger.info("Smallest version is %.1f MB, above the %d MB limit",
                        smallest["filesize"] / 1024 / 1024, limit // (1024 * 1024))
            yield smallest

    return selector


def selected_size(info: Optional[Dict[str, Any]]) -> int:
    """Size of the version yt-dlp picked (0 when unknown)."""
    if not info:
        return 0
    size = info.get("filesize") or info.get("filesize_approx")
    if not size and info.get("requested_formats"):
        size = sum((f.get("filesize") or f.get("filesize_approx") or 0) for f in info["requested_formats"])
    return int(size or 0)


def is_too_large(info: Optional[Dict[str, Any]]) -> bool:
    """True when yt-dlp skipped the download because the file is above the upload limit."""
    return bool(info) and downloaded_path(info) is None and selected_size(info) > MAX_UPLOAD_BYTES


def _extract(url: str, options: Dict[str, Any], download: bool) -> Optional[Dict[str, Any]]:
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=download)
        return ydl.sanitize_info(info) if info else None


def is_retryable(message: str) -> bool:
    return bool(_RETRYABLE.search(message or ""))


async def extract(url: str, options: Dict[str, Any], download: bool) -> Optional[Dict[str, Any]]:
    """Run yt-dlp in a worker thread, retrying transient errors.

    Returns None (and logs a warning) when the media cannot be fetched.
    """
    attempts = len(RETRY_DELAYS) + 1
    tracker = progress_tracker.get() if download else None
    if tracker is not None and "progress_hooks" not in options:
        def hook(status: Dict[str, Any]) -> None:
            # Runs in the yt-dlp thread; plain attribute writes only.
            done = status.get("downloaded_bytes") or status.get("total_bytes") or 0
            tracker.update(str(status.get("filename") or status.get("tmpfilename") or ""), int(done))
            if not tracker.total:
                tracker.total = int(status.get("total_bytes") or status.get("total_bytes_estimate") or 0)
        options["progress_hooks"] = [hook]
    for attempt in range(1, attempts + 1):
        try:
            if download:
                # Fragmented streams (HLS/DASH): fetch 16 fragments at a time.
                options.setdefault("concurrent_fragment_downloads", 16)
            loop = asyncio.get_running_loop()
            if not download:
                return await loop.run_in_executor(_metadata_pool, _extract, url, options, False)
            async with download_slot():
                return await loop.run_in_executor(_download_pool, _extract, url, options, True)
        except yt_dlp.utils.DownloadError as error:
            message = str(error)
            if attempt < attempts and is_retryable(message):
                delay = RETRY_DELAYS[attempt - 1]
                logger.info("yt-dlp attempt %d/%d failed for %s, retrying in %.0fs: %s",
                            attempt, attempts, url, delay, message[:160])
                await asyncio.sleep(delay)
                continue
            # Full message: it is what tells why a download (e.g. 4K) failed.
            logger.warning("yt-dlp could not process %s: %s", url, message[:1500])
        except Exception:
            logger.exception("yt-dlp crashed while processing %s", url)
        return None
    return None


async def resolve_url(url: str) -> str:
    """Follow redirects of short links (pin.it, t.snapchat.com, l.likee.video...)."""
    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with http_session().get(url, allow_redirects=True, timeout=timeout) as response:
            return str(response.url)
    except Exception as error:
        logger.debug("Could not resolve %s: %r", url, error)
        return url


async def fetch_text(url: str, headers: Optional[Dict[str, str]] = None) -> Optional[str]:
    try:
        timeout = aiohttp.ClientTimeout(total=20)
        async with http_session().get(url, allow_redirects=True, timeout=timeout, headers=headers) as response:
            if response.status != 200:
                logger.warning("GET %s -> HTTP %s", url, response.status)
                return None
            return await response.text(errors="replace")
    except Exception as error:
        logger.warning("GET %s failed: %r", url, error)
        return None


async def download_url(url: str, destination: Path, headers: Optional[Dict[str, str]] = None,
                       queue: bool = True) -> Optional[Path]:
    """Stream ``url`` to ``destination`` with aiohttp + aiofiles (never blocks the loop).

    ``queue=False`` for small files (covers, thumbnails): they skip the download queue.
    """
    try:
        timeout = aiohttp.ClientTimeout(total=300, sock_read=60)
        async with (download_slot() if queue else _no_slot()):
            async with http_session().get(url, timeout=timeout, headers=headers) as response:
                if response.status != 200:
                    logger.warning("Download %s -> HTTP %s", url[:120], response.status)
                    return None
                if (response.content_length or 0) > MAX_UPLOAD_BYTES:
                    logger.warning("Download %s is above the upload limit", url[:120])
                    raise FileTooLargeError(url)
                size = 0
                async with aiofiles.open(destination, "wb") as file:
                    async for chunk in response.content.iter_chunked(256 * 1024):
                        size += len(chunk)
                        if size > MAX_UPLOAD_BYTES:
                            logger.warning("Download %s exceeded the upload limit", url[:120])
                            break
                        await file.write(chunk)
                if size > MAX_UPLOAD_BYTES:
                    destination.unlink(missing_ok=True)
                    raise FileTooLargeError(url)
        return destination if destination.stat().st_size > 0 else None
    except FileTooLargeError:
        raise
    except Exception as error:
        logger.warning("Download %s failed: %r", url[:120], error)
        return None


PARALLEL_CONNECTIONS: int = 6  # per stream (video and audio are fetched at the same time)
PARALLEL_PIECE_MAX: int = 8 * 1024 * 1024
PARALLEL_PIECE_MIN: int = 1024 * 1024
PARALLEL_PIECE_ATTEMPTS: int = 6
# YouTube throttles some connections at random (a few KB/s, or a reset after a
# minute). A piece slower than this after SLOW_AFTER seconds is dropped and the
# rest of it is requested again on a fresh connection.
MIN_PIECE_SPEED: int = 512 * 1024
SLOW_AFTER: float = 4.0


class ParallelDownloadError(Exception):
    """A ranged download did not work out; the caller falls back to yt-dlp."""


class _SlowPiece(Exception):
    pass


async def _exact_size(url: str, headers: Dict[str, str]) -> Optional[int]:
    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with http_session().head(url, headers=headers, timeout=timeout, allow_redirects=True) as response:
            return response.content_length if response.status == 200 else None
    except Exception:
        return None


async def fetch_ranges(url: str, headers: Dict[str, str], size: int, destination: Path,
                       progress: Optional[DownloadProgress] = None,
                       connections: int = PARALLEL_CONNECTIONS) -> None:
    """Download ``url`` (``size`` bytes) over several connections at once.

    The file is cut into pieces (1-8 MB) fetched with HTTP Range requests by
    ``connections`` workers. YouTube limits the speed of each connection, so this
    is several times faster than one stream. A piece that fails or crawls is
    resumed from where it stopped on a new connection. Raises
    ParallelDownloadError when a piece keeps failing.
    """
    piece_size = max(PARALLEL_PIECE_MIN, min(PARALLEL_PIECE_MAX, size // (connections * 4) or 1))
    queue: asyncio.Queue = asyncio.Queue()
    for start in range(0, size, piece_size):
        queue.put_nowait((start, min(start + piece_size, size) - 1))
    pieces = queue.qsize()
    done: Dict[int, int] = {}
    key = str(destination)
    timeout = aiohttp.ClientTimeout(total=None, sock_connect=15, sock_read=15)
    fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)

    async def fetch_piece(start: int, offset: int, end: int, check_speed: bool) -> int:
        """Fetch bytes offset..end of the piece starting at ``start``; returns the new offset."""
        request_headers = dict(headers, Range="bytes=%d-%d" % (offset, end))
        began, first = time.monotonic(), offset
        async with http_session().get(url, headers=request_headers, timeout=timeout) as response:
            if response.status != 206:
                raise ParallelDownloadError("HTTP %s for bytes %d-%d" % (response.status, offset, end))
            async for chunk in response.content.iter_chunked(256 * 1024):
                if offset + len(chunk) > end + 1:
                    raise ParallelDownloadError("server sent more than requested")
                os.pwrite(fd, chunk, offset)
                offset += len(chunk)
                done[start] = offset - start
                if progress is not None:
                    progress.update(key, sum(done.values()))
                elapsed = time.monotonic() - began
                if check_speed and offset <= end and elapsed > SLOW_AFTER \
                        and (offset - first) / elapsed < MIN_PIECE_SPEED:
                    raise _SlowPiece(offset)
        return offset

    async def worker() -> None:
        while not queue.empty():
            start, end = queue.get_nowait()
            offset = start
            for attempt in range(1, PARALLEL_PIECE_ATTEMPTS + 1):
                last = attempt == PARALLEL_PIECE_ATTEMPTS
                try:
                    offset = await fetch_piece(start, offset, end, check_speed=not last)
                    if offset == end + 1:
                        break
                    error: Exception = ParallelDownloadError("connection closed early")
                except _SlowPiece:
                    offset = start + done.get(start, 0)
                    continue  # resume at once on a new connection
                except (aiohttp.ClientError, asyncio.TimeoutError, ParallelDownloadError) as failure:
                    error = failure
                    offset = start + done.get(start, 0)  # bytes already written stay valid
                if last:
                    raise ParallelDownloadError("bytes %d-%d: %r" % (start, end, error))
                await asyncio.sleep(min(attempt, 3))
            else:
                raise ParallelDownloadError("bytes %d-%d: too slow" % (start, end))

    try:
        os.ftruncate(fd, size)
        workers = [asyncio.create_task(worker()) for _ in range(max(1, min(connections, pieces)))]
        try:
            await asyncio.gather(*workers)
        except BaseException:
            for task in workers:
                task.cancel()
            await asyncio.gather(*workers, return_exceptions=True)
            raise
    finally:
        os.close(fd)


def _plain_http(fmt: Dict[str, Any]) -> bool:
    return bool(fmt.get("url")) and str(fmt.get("protocol") or "") in ("http", "https")


async def download_parallel(info: Dict[str, Any], job_dir: Path, name: str,
                            progress: Optional[DownloadProgress] = None) -> Optional[Path]:
    """Fetch the version yt-dlp selected in ``info`` (extracted with download=False)
    with parallel ranged requests and merge video + audio into ``name``.mp4.

    Returns None when the selection is not suited (HLS, unknown size, not MP4):
    the caller then lets yt-dlp download it. Raises ParallelDownloadError if a
    suited download fails, FileTooLargeError if it is above the upload limit.
    """
    parts = info.get("requested_formats") or [info]
    if not all(_plain_http(part) for part in parts):
        return None
    if len(parts) == 1 and parts[0].get("ext") != "mp4":
        return None
    if len(parts) > 2:
        return None
    sizes: List[int] = []
    for part in parts:
        headers = part.get("http_headers") or BROWSER_HEADERS
        # filesize from YouTube is exact (its "clen"); filesize_approx is not.
        size = part.get("filesize") or await _exact_size(part["url"], headers)
        if not size:
            return None
        sizes.append(int(size))
    if sum(sizes) > MAX_UPLOAD_BYTES:
        raise FileTooLargeError(info.get("webpage_url") or name)
    if progress is not None:
        progress.total = sum(sizes)

    files = [job_dir / ("%s.part%d" % (name, index)) for index in range(len(parts))]
    output = job_dir / ("%s.mp4" % name)
    try:
        async with download_slot():
            await asyncio.gather(*(
                fetch_ranges(part["url"], part.get("http_headers") or BROWSER_HEADERS, size, path, progress)
                for part, size, path in zip(parts, sizes, files)
            ))
        if len(parts) == 1:
            files[0].rename(output)
            return output
        video = next((i for i, p in enumerate(parts) if p.get("vcodec") not in (None, "none")), 0)
        audio = 1 - video
        # Same as yt-dlp's own merge: streams copied as they are, index at the front.
        merged = await run_ffmpeg(
            "-y", "-i", str(files[video]), "-i", str(files[audio]),
            "-c", "copy", "-map", "0:v:0", "-map", "1:a:0", "-movflags", "+faststart",
            "-f", "mp4", str(output),
        )
        if merged is None or not output.is_file() or output.stat().st_size == 0:
            raise ParallelDownloadError("merging the video and audio failed")
        return output
    except BaseException:
        output.unlink(missing_ok=True)
        raise
    finally:
        for path in files:
            path.unlink(missing_ok=True)


async def read_bytes(path: Path) -> bytes:
    async with aiofiles.open(path, "rb") as file:
        return await file.read()


def downloaded_path(info: Dict[str, Any]) -> Optional[Path]:
    """Return the final file yt-dlp wrote for one (non-playlist) entry."""
    for item in info.get("requested_downloads") or []:
        path = item.get("filepath")
        if path and os.path.isfile(path):
            return Path(path)
    path = info.get("filepath") or info.get("_filename")
    return Path(path) if path and os.path.isfile(path) else None


def fits_upload_limit(path: Path) -> bool:
    size = path.stat().st_size
    if size > MAX_UPLOAD_BYTES:
        logger.warning("%s is %.1f MB, above the Telegram upload limit", path.name, size / 1024 / 1024)
        return False
    return size > 0


async def run_ffmpeg(*args: str, stdin: Optional[bytes] = None) -> Optional[bytes]:
    """Run ffmpeg and return its stdout, or None if it failed.

    At most one ffmpeg per CPU core runs at a time; the rest wait (without
    blocking the event loop), so a burst of conversions cannot starve the server.
    """
    async with _ffmpeg_slots:
        process = await asyncio.create_subprocess_exec(
            "ffmpeg", "-hide_banner", "-loglevel", "error", *args,
            stdin=asyncio.subprocess.PIPE if stdin is not None else asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate(input=stdin)
    if process.returncode != 0:
        logger.warning("ffmpeg failed: %s", stderr.decode(errors="replace")[:300])
        return None
    return stdout


# Videos sent before this moment were uploaded without width/height, so Telegram
# shows them as 1:1 squares. Their cached file_ids are ignored and replaced.
VIDEO_CACHE_VALID_FROM = datetime.datetime(2026, 11, 23, 16, 10, tzinfo=datetime.timezone.utc)


async def video_meta(source: Optional[str]) -> Dict[str, int]:
    """Real width/height/duration of a local video, for send_video / InputMediaVideo.

    Without width and height Telegram cannot know the shape and shows the video
    as a square; with them it keeps the original 16:9 / 9:16 / ... ratio. The file
    itself is never touched. Returns {} for URLs, file_ids or when ffprobe fails.
    """
    if not source or not os.path.isabs(source) or not os.path.isfile(source):
        return {}
    try:
        process = await asyncio.create_subprocess_exec(
            "ffprobe", "-v", "error", "-select_streams", "v:0", "-print_format", "json",
            "-show_entries", "stream=width,height,duration:stream_tags=rotate:stream_side_data=rotation:format=duration",
            source, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _stderr = await asyncio.wait_for(process.communicate(), timeout=20)
        data = json.loads(stdout or b"{}")
    except Exception as error:
        logger.warning("ffprobe failed for %s: %r", source, error)
        return {}
    streams = data.get("streams") or []
    if not streams:
        return {}
    stream = streams[0]
    width, height = int(stream.get("width") or 0), int(stream.get("height") or 0)
    rotation = (stream.get("tags") or {}).get("rotate")
    for side in stream.get("side_data_list") or []:
        rotation = side.get("rotation", rotation)
    # Phone videos are often stored landscape with a 90 degree rotation flag.
    if rotation is not None and abs(int(float(rotation))) % 180 == 90:
        width, height = height, width
    meta: Dict[str, int] = {}
    if width and height:
        meta.update(width=width, height=height)
    duration = stream.get("duration") or (data.get("format") or {}).get("duration")
    try:
        if duration and float(duration) > 0:
            meta["duration"] = int(round(float(duration)))
    except (TypeError, ValueError):
        pass
    return meta


VIDEO_SOURCE_TTL: int = 30 * 24 * 3600


def _source_key(file_unique_id: str) -> str:
    return "video_source:%s" % file_unique_id


async def remember_video_source(sent: Any, url: str) -> None:
    """Remember which link a video the bot sent came from.

    Telegram only lets bots download files up to 20 MB, so "recognize music" on a
    bigger video the bot sent itself takes a short audio sample from this link.
    """
    video = getattr(sent, "video", None)
    if video is None or not url:
        return
    from core.cache import cache
    with suppress(Exception):
        await cache.set(_source_key(video.file_unique_id), url, ttl=VIDEO_SOURCE_TTL)


async def video_source(file_unique_id: str) -> Optional[str]:
    from core.cache import cache
    with suppress(Exception):
        return await cache.get(_source_key(file_unique_id))
    return None


async def audio_sample_from_source(url: str, seconds: int = 60) -> Optional[bytes]:
    """First ``seconds`` of a link's audio as 16 kHz mono WAV (streams only that part)."""
    MEDIA_TMP_DIR.mkdir(parents=True, exist_ok=True)
    options = base_options(MEDIA_TMP_DIR, _platform_of(url))
    options.update(format="ba[ext=m4a]/ba/b[acodec!=none]/b", noplaylist=True)
    info = await extract(url, options, download=False)
    if info and info.get("entries"):
        info = next((e for e in info["entries"] if e), None)
    stream = (info or {}).get("url")
    if not stream:
        return None
    headers = "".join("%s: %s\r\n" % item for item in ((info or {}).get("http_headers") or {}).items())
    with tempfile.NamedTemporaryFile(suffix=".wav", dir=MEDIA_TMP_DIR) as tmp:
        args = ["-y"]
        if headers:
            args += ["-headers", headers]
        args += ["-t", str(seconds), "-i", stream, "-vn", "-ac", "1", "-ar", "16000", tmp.name]
        if await run_ffmpeg(*args) is None:
            return None
        return await read_bytes(Path(tmp.name)) or None


def _platform_of(url: str) -> str:
    host = url.lower()
    for name in ("instagram", "tiktok", "youtube", "pinterest", "snapchat", "likee"):
        if name in host or (name == "youtube" and "youtu.be" in host):
            return name
    return "generic"


def discard(*sources: Optional[str]) -> None:
    """Delete the job directories of downloaded files (no-op for URLs / file_ids)."""
    for source in sources:
        if not source:
            continue
        try:
            parent = Path(source).resolve().parent
        except (OSError, ValueError):
            continue
        if parent.parent == MEDIA_TMP_DIR.resolve():
            shutil.rmtree(parent, ignore_errors=True)


def discard_dir(job_dir: Optional[Path]) -> None:
    """Remove a job directory after a failed download (only inside MEDIA_TMP_DIR)."""
    if job_dir is not None and job_dir.resolve().parent == MEDIA_TMP_DIR.resolve():
        shutil.rmtree(job_dir, ignore_errors=True)


def as_input_file(source: str, filename: Optional[str] = None, timeout: int = 300) -> Union[InputFile, str]:
    """Local path -> FSInputFile (or a file:// path, see below), anything else -> URLInputFile.

    With a local Bot API server that can see MEDIA_TMP_DIR (mounted read-only into
    its container), files are passed as ``file:///path``: the server reads them from
    disk instead of the bot streaming a second copy to it over HTTP.
    """
    if os.path.isabs(source) and os.path.isfile(source):
        same_name = filename is None or filename == os.path.basename(source)
        if config.telegram_api_local and same_name and _in_media_dir(source):
            return "file://" + os.path.abspath(source)
        # 1 MB chunks: far fewer thread hops than aiogram's 64 kB default for big files.
        return FSInputFile(source, filename=filename, chunk_size=1024 * 1024)
    return URLInputFile(source, filename=filename, timeout=timeout)


def _in_media_dir(path: str) -> bool:
    try:
        return Path(path).resolve().is_relative_to(MEDIA_TMP_DIR.resolve())
    except (OSError, ValueError):
        return False


__all__ = [
    "BROWSER_HEADERS",
    "MEDIA_TMP_DIR",
    "MAX_DOWNLOADS_PER_USER",
    "MAX_UPLOAD_BYTES",
    "FileTooLargeError",
    "MAX_TELEGRAM_DOWNLOAD_BYTES",
    "MAX_UPLOAD_MB",
    "STANDARD_QUALITIES",
    "VIDEO_CACHE_VALID_FROM",
    "codec_score",
    "quality_of",
    "audio_sample_from_source",
    "remember_video_source",
    "video_source",
    "close_http_session",
    "configure_executors",
    "shutdown_executors",
    "download_slot",
    "http_session",
    "is_too_large",
    "load_status",
    "queue_notifier",
    "selected_size",
    "size_aware_format",
    "as_input_file",
    "video_meta",
    "base_options",
    "discard",
    "discard_dir",
    "download_url",
    "downloaded_path",
    "extract",
    "fetch_text",
    "fits_upload_limit",
    "is_retryable",
    "new_job_dir",
    "read_bytes",
    "resolve_url",
    "run_ffmpeg",
    "user_download_slot",
]

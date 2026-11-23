"""Shared helpers for the local, free media modules (yt-dlp + ffmpeg).

Everything here runs on this server: no third-party API is involved.
Blocking work (yt-dlp, ffmpeg) is pushed to worker threads so the bot's
event loop never stalls, and a semaphore caps how many downloads run at once.
"""
import asyncio
import logging
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional

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
MAX_PARALLEL_DOWNLOADS: int = 3
TMP_MAX_AGE_SECONDS: int = 60 * 60

_semaphore = asyncio.Semaphore(MAX_PARALLEL_DOWNLOADS)


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
    """Create a fresh working directory for one download (old ones are purged)."""
    MEDIA_TMP_DIR.mkdir(parents=True, exist_ok=True)
    _purge_old_dirs()
    return Path(tempfile.mkdtemp(dir=MEDIA_TMP_DIR))


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
    )
    cookies = cookie_file(platform)
    if cookies:
        options["cookiefile"] = cookies
    return options


def _extract(url: str, options: Dict[str, Any], download: bool) -> Optional[Dict[str, Any]]:
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=download)
        return ydl.sanitize_info(info) if info else None


async def extract(url: str, options: Dict[str, Any], download: bool) -> Optional[Dict[str, Any]]:
    """Run yt-dlp in a worker thread. Returns None (and logs a warning) on any failure."""
    try:
        if not download:
            return await asyncio.to_thread(_extract, url, options, False)
        async with _semaphore:
            return await asyncio.to_thread(_extract, url, options, True)
    except yt_dlp.utils.DownloadError as error:
        logger.warning("yt-dlp could not process %s: %s", url, str(error)[:300])
    except Exception:
        logger.exception("yt-dlp crashed while processing %s", url)
    return None


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
    """Run ffmpeg and return its stdout, or None if it failed."""
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


def as_input_file(source: str, filename: Optional[str] = None, timeout: int = 300) -> InputFile:
    """Local path -> FSInputFile, anything else -> URLInputFile."""
    if os.path.isabs(source) and os.path.isfile(source):
        return FSInputFile(source, filename=filename)
    return URLInputFile(source, filename=filename, timeout=timeout)


__all__ = [
    "MEDIA_TMP_DIR",
    "MAX_UPLOAD_BYTES",
    "as_input_file",
    "base_options",
    "discard",
    "downloaded_path",
    "extract",
    "fits_upload_limit",
    "new_job_dir",
    "run_ffmpeg",
]

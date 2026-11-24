"""Turn any video into a Telegram video note ("round video"), and back.

Telegram shows a square MP4 sent with sendVideoNote as a circle, so the video is
centre-cropped to a square, scaled to at most 640x640 and cut to 60 seconds
(both are Telegram's video note limits), then encoded as H.264 + AAC.

The reverse needs no mask removal: a video note *file* is already a plain square
MP4 (the circle is drawn by the Telegram app). It is sent again as a normal
video, at its original resolution and without re-encoding when possible.
"""
import asyncio
import json
import logging
import os
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Optional

from aiogram import Bot

from services.media_downloader import discard_dir, new_job_dir, run_ffmpeg, video_meta

logger = logging.getLogger(__name__)

MAX_SIDE: int = 640
MAX_SECONDS: int = 60


@dataclass
class VideoNote:
    path: Path
    length: int        # width = height of the square, in pixels
    duration: int      # seconds
    truncated: bool    # the source was longer than MAX_SECONDS
    job_dir: Path


async def _local_copy(bot: Bot, file_id: str, job_dir: Path) -> tuple[Path, bool]:
    """Path ffmpeg can read, and whether it must be removed afterwards.

    With a local Bot API server getFile returns a file already on this machine;
    on api.telegram.org the file is downloaded into ``job_dir``.
    """
    file = await bot.get_file(file_id)
    path = file.file_path or ""
    if os.path.isabs(path) and os.path.exists(path):
        return Path(path), True
    destination = job_dir / "source"
    buffer = BytesIO()
    await bot.download_file(path, destination=buffer)
    destination.write_bytes(buffer.getvalue())
    return destination, False


async def make_video_note(bot: Bot, file_id: str) -> Optional[VideoNote]:
    """Download the Telegram video ``file_id`` and convert it; None if it cannot be converted.

    The caller sends ``VideoNote.path`` and then calls :func:`discard_dir` on ``job_dir``.
    """
    job_dir = new_job_dir()
    source: Optional[Path] = None
    remove_source = False
    try:
        source, remove_source = await _local_copy(bot, file_id, job_dir)
        meta = await video_meta(str(source))
        width, height = meta.get("width") or 0, meta.get("height") or 0
        if not (width and height):
            logger.info("Video note: %s has no video stream", file_id)
            discard_dir(job_dir)
            return None
        # Never upscale small videos; even sizes are required by H.264 (yuv420p).
        side = min(MAX_SIDE, width, height) // 2 * 2
        duration = meta.get("duration") or 0
        output = job_dir / "round.mp4"
        result = await run_ffmpeg(
            "-y", "-t", str(MAX_SECONDS), "-i", str(source),
            "-map", "0:v:0", "-map", "0:a:0?",
            # Centre square of the (auto-rotated) frame, then the target size.
            "-vf", "crop='min(iw,ih)':'min(iw,ih)',scale=%d:%d:flags=lanczos,setsar=1,fps='min(source_fps,30)'" % (side, side),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-profile:v", "main", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k", "-ac", "2",
            "-movflags", "+faststart",
            str(output),
        )
        if result is None or not output.is_file() or output.stat().st_size == 0:
            discard_dir(job_dir)
            return None
        return VideoNote(
            path=output,
            length=side,
            duration=min(duration, MAX_SECONDS) if duration else MAX_SECONDS,
            truncated=duration > MAX_SECONDS,
            job_dir=job_dir,
        )
    except Exception:
        logger.exception("Video note conversion failed for %s", file_id)
        discard_dir(job_dir)
        return None
    finally:
        if remove_source and source is not None:
            try:
                os.remove(source)
            except OSError:
                logger.warning("Cannot remove downloaded file %s", source)


async def _codecs(path: Path) -> tuple[Optional[str], Optional[str]]:
    """(video codec, audio codec) of ``path``; None for a missing stream."""
    process = await asyncio.create_subprocess_exec(
        "ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name", "-of", "json", str(path),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
    )
    stdout, _stderr = await asyncio.wait_for(process.communicate(), timeout=20)
    streams = json.loads(stdout or b"{}").get("streams") or []
    first = lambda kind: next((st.get("codec_name") for st in streams if st.get("codec_type") == kind), None)  # noqa: E731
    return first("video"), first("audio")


@dataclass
class RegularVideo:
    path: Path
    width: int
    height: int
    duration: int
    job_dir: Path


async def make_regular_video(bot: Bot, file_id: str) -> Optional[RegularVideo]:
    """Turn the video note ``file_id`` into a normal MP4 video; None on failure.

    The streams are copied as they are (same resolution and quality, takes a
    moment); only a file that cannot be copied into MP4 is re-encoded.
    The caller sends ``RegularVideo.path`` and then calls :func:`discard_dir` on ``job_dir``.
    """
    job_dir = new_job_dir()
    source: Optional[Path] = None
    remove_source = False
    try:
        source, remove_source = await _local_copy(bot, file_id, job_dir)
        output = job_dir / "video.mp4"
        video_codec, audio_codec = await _codecs(source)
        # Copy what every Telegram app plays (H.264 + AAC) as it is; re-encode the rest.
        video_args = ["-c:v", "copy"] if video_codec == "h264" else \
            ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p"]
        audio_args = ["-c:a", "copy"] if audio_codec in ("aac", None) else ["-c:a", "aac", "-b:a", "128k"]
        result = await run_ffmpeg(
            "-y", "-i", str(source), "-map", "0:v:0", "-map", "0:a:0?",
            *video_args, *audio_args, "-movflags", "+faststart", str(output),
        )
        if result is None or not output.is_file() or output.stat().st_size == 0:
            discard_dir(job_dir)
            return None
        meta = await video_meta(str(output))
        return RegularVideo(
            path=output,
            width=meta.get("width") or 0,
            height=meta.get("height") or 0,
            duration=meta.get("duration") or 0,
            job_dir=job_dir,
        )
    except Exception:
        logger.exception("Video note to video conversion failed for %s", file_id)
        discard_dir(job_dir)
        return None
    finally:
        if remove_source and source is not None:
            try:
                os.remove(source)
            except OSError:
                logger.warning("Cannot remove downloaded file %s", source)

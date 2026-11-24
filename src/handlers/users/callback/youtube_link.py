import asyncio
import logging
import time
from contextlib import suppress
from html import escape
from pathlib import Path
from typing import Optional

from aiogram import F, Router
from aiogram.types import CallbackQuery, FSInputFile
from aiogram.utils.i18n import gettext as _

from core.cache import cache
from core.config import config
from database.models import User, UserPreferences
from filters.callback.youtube_link import YoutubeLinkCallback
from filters.callback.youtube_quality import YoutubeQualityCallback
from keyboard.inline import VideoRecognizeKeyboard
from services.media_downloader import (
    MAX_UPLOAD_BYTES,
    MAX_UPLOAD_MB,
    DownloadProgress,
    FileTooLargeError,
    as_input_file,
    discard,
    progress_tracker,
    remember_video_source,
    video_meta,
)
from services.youtube.audio import YouTubeAudioSender
from services.youtube_api import MediaFile, YouTubeAPI, watch_url
from utils.helpers import safe_delete
from utils.helpers.media_errors import file_too_large_text

router = Router()
logger = logging.getLogger(__name__)

VIDEO_UPLOAD_TIMEOUT: int = 300
PROGRESS_INTERVAL: float = 10.0
# Above this size sending takes a while too, so the user is told it is being sent.
SHOW_UPLOAD_FROM_BYTES: int = 50 * 1024 * 1024
# Telegram keeps every file the bot sent: the same video at the same quality is
# re-sent by file_id at once instead of being downloaded and uploaded again.
SENT_VIDEO_TTL: int = 60 * 24 * 3600


def _sent_key(video_id: str, quality: Optional[int]) -> str:
    return "ytvideo:%s:%s" % (video_id, quality or "auto")


async def _cached_file(video_id: str, quality: Optional[int]) -> Optional[dict]:
    try:
        return await cache.get(_sent_key(video_id, quality))
    except Exception as error:
        logger.debug("sent-video cache read failed: %r", error)
        return None


async def _remember_file(video_id: str, quality: Optional[int], sent, title: str) -> None:
    video = getattr(sent, "video", None)
    if video is None:
        return
    try:
        await cache.set(_sent_key(video_id, quality), dict(file_id=video.file_id, title=title), ttl=SENT_VIDEO_TTL)
    except Exception as error:
        logger.debug("sent-video cache write failed: %r", error)


def _caption(title: str) -> str:
    footer = _("Find any music you want quickly and easily via %(username_bot)s!") % dict(
        username_bot=config.telegram_username,
    )
    return "<b>%s</b>\n\n%s" % (escape(title), footer) if title else footer


async def _show_progress(message, progress: DownloadProgress) -> None:
    """Edit ``message`` to "⏳ Downloading... X%" every PROGRESS_INTERVAL seconds."""
    shown = None
    while True:
        await asyncio.sleep(PROGRESS_INTERVAL)
        percent = progress.percent
        if percent is None or percent == shown:
            continue
        with suppress(Exception):  # e.g. the user deleted it; never break the download
            await message.edit_text(_("⏳ Downloading... %(percent)s%%") % dict(percent=percent))
            shown = percent


def _lower_quality_text() -> str:
    return _("❌ The file is too large (over %(limit)sMB). Please choose a lower quality.") % dict(limit=MAX_UPLOAD_MB)


async def _send_video(callback: CallbackQuery, video_id: str, quality: Optional[int] = None) -> None:
    """Download ``video_id`` (exactly ``quality`` if given, else best up to 720p) and send it."""
    cached = await _cached_file(video_id, quality)
    if cached:
        try:
            sent = await callback.message.answer_video(
                video=cached["file_id"],
                caption=_caption(cached.get("title") or ""),
                reply_markup=VideoRecognizeKeyboard.make(),
            )
            await remember_video_source(sent, watch_url(video_id))
            return
        except Exception as error:
            logger.info("Cached file_id for %s (%sp) not usable, downloading again: %r", video_id, quality, error)

    processing = await callback.message.answer(text=_("Processing..."))
    video: Optional[MediaFile] = None
    thumb: Optional[Path] = None
    started = time.monotonic()
    progress = DownloadProgress()
    token = progress_tracker.set(progress)
    updater = asyncio.create_task(_show_progress(processing, progress))
    try:
        try:
            video = await YouTubeAPI.download_video(url=watch_url(video_id), quality=quality)
        finally:
            updater.cancel()
            progress_tracker.reset(token)
        downloaded = time.monotonic()
        if not video:
            await callback.message.answer(text=_("Could not fetch the video."))
            return
        if video.filesize >= SHOW_UPLOAD_FROM_BYTES:
            with suppress(Exception):
                await processing.edit_text(_("📤 Sending the video..."))
        thumb = await YouTubeAPI.thumbnail_file(video_id)
        meta = await video_meta(str(video.path))
        sent = await callback.message.answer_video(
            video=as_input_file(str(video.path), filename="%s.mp4" % video_id, timeout=VIDEO_UPLOAD_TIMEOUT),
            thumbnail=FSInputFile(thumb) if thumb else None,
            caption=_caption(video.title),
            duration=meta.get("duration") or int(video.duration) or None,
            width=meta.get("width") or video.width,
            height=meta.get("height") or video.height,
            supports_streaming=True,
            reply_markup=VideoRecognizeKeyboard.make(),
        )
        sent_at = time.monotonic()
        logger.info(
            "YouTube %s %sp: %.1f MB, download %.1fs, upload %.1fs",
            video_id, quality or "auto", video.filesize / 1e6, downloaded - started, sent_at - downloaded,
        )
        await remember_video_source(sent, watch_url(video_id))
        await _remember_file(video_id, quality, sent, video.title)
    except FileTooLargeError:
        await callback.message.answer(text=_lower_quality_text() if quality else file_too_large_text())
    except Exception:
        logger.exception("YouTube video download failed for %s (%sp)", video_id, quality)
        await callback.message.answer(text=_("Could not fetch the video."))
    finally:
        discard(str(video.path) if video else None, str(thumb) if thumb else None)
        await safe_delete(processing)


async def _send_audio(callback: CallbackQuery, video_id: str, user: User) -> None:
    processing = await callback.message.answer(text=_("Processing..."))
    try:
        prefs, __ = await UserPreferences.get_or_create(user=user)
        sent = await YouTubeAudioSender.send(
            target=callback.message,
            video_id=video_id,
            like_buttons=prefs.like_buttons,
        )
    except Exception:
        logger.exception("YouTube audio download failed for %s", video_id)
        sent = False
    finally:
        await safe_delete(processing)
    if not sent:
        await callback.message.answer(text=_("Download failed."))


@router.callback_query(YoutubeQualityCallback.filter((F.platform == "yt") & (F.quality == "audio")))
async def youtube_quality_audio_handler(callback: CallbackQuery, callback_data: YoutubeQualityCallback, user: User) -> None:
    await callback.answer()
    await _send_audio(callback, callback_data.video_id, user)


@router.callback_query(YoutubeQualityCallback.filter((F.platform == "yt") & F.quality.regexp(r"^\d{3,4}$")))
async def youtube_quality_video_handler(callback: CallbackQuery, callback_data: YoutubeQualityCallback) -> None:
    quality = int(callback_data.quality)
    # The preview already knows each resolution's smallest size: answer at once
    # instead of starting a download that cannot fit.
    info = await YouTubeAPI.cached_info(callback_data.video_id)
    size = (info.qualities.get(callback_data.quality) or 0) if info else 0
    if size > MAX_UPLOAD_BYTES:
        await callback.answer(_lower_quality_text(), show_alert=True)
        return
    await callback.answer()
    await _send_video(callback, callback_data.video_id, quality)


# Buttons of previews sent before resolutions were offered ("📼 Video" / "🎧 Audio").
@router.callback_query(YoutubeLinkCallback.filter(F.kind == "video"))
async def youtube_link_video_handler(callback: CallbackQuery, callback_data: YoutubeLinkCallback) -> None:
    await callback.answer()
    await _send_video(callback, callback_data.video_id)


@router.callback_query(YoutubeLinkCallback.filter(F.kind == "audio"))
async def youtube_link_audio_handler(callback: CallbackQuery, callback_data: YoutubeLinkCallback, user: User) -> None:
    await callback.answer()
    await _send_audio(callback, callback_data.video_id, user)

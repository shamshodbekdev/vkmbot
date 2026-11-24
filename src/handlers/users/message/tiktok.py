import logging

from aiogram import F, Router
from aiogram.types import Message
from aiogram.utils.i18n import gettext as _

from core.config import config
from database.models import TikTokMedia
from filters.common import TikTokUrlFilter
from keyboard.inline import VideoRecognizeKeyboard
from services.media_downloader import (
    VIDEO_CACHE_VALID_FROM,
    FileTooLargeError,
    as_input_file,
    discard,
    remember_video_source,
    video_meta,
)
from services.tiktok import TikTokConvert
from utils.helpers import safe_delete
from utils.helpers.media_errors import file_too_large_text

router = Router()
logger = logging.getLogger(__name__)

VIDEO_UPLOAD_TIMEOUT: int = 300


def _caption() -> str:
    return _("Find any music you want quickly and easily via %(username_bot)s!") % dict(
        username_bot=config.telegram_username,
    )


@router.message(F.text, TikTokUrlFilter())
async def tiktok_handler(message: Message, tiktok_url: str) -> None:
    processing = await message.answer(text=_("Processing..."))
    video = None
    try:
        result = await TikTokConvert.convert(url=tiktok_url)
        if not result or not result.id:
            await message.answer(text=_("Could not fetch the TikTok video."))
            return

        video_id = result.id
        cached = await TikTokMedia.filter(video_id=video_id, created_at__gte=VIDEO_CACHE_VALID_FROM).first()
        if cached:
            sent = await message.answer_video(
                video=cached.file_id,
                caption=_caption(),
                reply_markup=VideoRecognizeKeyboard.make(),
            )
            await remember_video_source(sent, tiktok_url)
            return

        video = await TikTokConvert.download(url=tiktok_url)
        if not video or not video.play:
            await message.answer(text=_("Could not fetch the TikTok video."))
            return

        meta = await video_meta(video.play)
        meta.setdefault("duration", video.duration)
        sent = await message.answer_video(
            video=as_input_file(video.play, timeout=VIDEO_UPLOAD_TIMEOUT),
            supports_streaming=True,
            **meta,
            caption=_caption(),
            reply_markup=VideoRecognizeKeyboard.make(),
        )
        await remember_video_source(sent, tiktok_url)
        if sent.video:
            # Replaces a stale (pre-fix, square) cache row for this video, if any.
            await TikTokMedia.filter(video_id=video_id).delete()
            await TikTokMedia.create(video_id=video_id, file_id=sent.video.file_id)
    except FileTooLargeError:
        await message.answer(text=file_too_large_text())
    except Exception:
        logger.exception("TikTok download failed for %s", tiktok_url)
        await message.answer(text=_("Could not fetch the TikTok video."))
    finally:
        discard(video.play if video else None)
        await safe_delete(processing)

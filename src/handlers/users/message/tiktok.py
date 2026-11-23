import logging

from aiogram import F, Router
from aiogram.types import Message
from aiogram.utils.i18n import gettext as _

from core.config import config
from database.models import TikTokMedia
from filters.common import TikTokUrlFilter
from keyboard.inline import VideoRecognizeKeyboard
from services.media_downloader import as_input_file, discard
from services.tiktok import TikTokConvert
from utils.helpers import safe_delete

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
        cached = await TikTokMedia.get_or_none(video_id=video_id)
        if cached:
            await message.answer_video(
                video=cached.file_id,
                caption=_caption(),
                reply_markup=VideoRecognizeKeyboard.make(),
            )
            return

        video = await TikTokConvert.download(url=tiktok_url)
        if not video or not video.play:
            await message.answer(text=_("Could not fetch the TikTok video."))
            return

        sent = await message.answer_video(
            video=as_input_file(video.play, timeout=VIDEO_UPLOAD_TIMEOUT),
            duration=video.duration,
            supports_streaming=True,
            caption=_caption(),
            reply_markup=VideoRecognizeKeyboard.make(),
        )
        if sent.video:
            await TikTokMedia.get_or_create(video_id=video_id, defaults=dict(file_id=sent.video.file_id))
    except Exception:
        logger.exception("TikTok download failed for %s", tiktok_url)
        await message.answer(text=_("Could not fetch the TikTok video."))
    finally:
        discard(video.play if video else None)
        await safe_delete(processing)

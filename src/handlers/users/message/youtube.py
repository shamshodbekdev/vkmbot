import logging

from aiogram import F, Router
from aiogram.types import Message
from aiogram.utils.i18n import gettext as _

from core.config import config
from filters.common import YouTubeUrlFilter
from keyboard.inline import VideoRecognizeKeyboard
from services.media_downloader import as_input_file, discard
from services.youtube_api import YouTubeAPI
from utils.helpers import safe_delete

router = Router()
logger = logging.getLogger(__name__)

VIDEO_UPLOAD_TIMEOUT: int = 300


def _caption() -> str:
    return _("Find any music you want quickly and easily via %(username_bot)s!") % dict(
        username_bot=config.telegram_username,
    )


@router.message(F.text, YouTubeUrlFilter())
async def youtube_handler(message: Message, youtube_url: str) -> None:
    processing = await message.answer(text=_("Processing..."))
    video = None
    try:
        video = await YouTubeAPI.download_video(url=youtube_url)
        if not video:
            await message.answer(text=_("Could not fetch the video."))
            return
        await message.answer_video(
            video=as_input_file(str(video.path), timeout=VIDEO_UPLOAD_TIMEOUT),
            duration=int(video.duration) or None,
            supports_streaming=True,
            caption=_caption(),
            reply_markup=VideoRecognizeKeyboard.make(),
        )
    except Exception:
        logger.exception("YouTube download failed for %s", youtube_url)
        await message.answer(text=_("Could not fetch the video."))
    finally:
        discard(str(video.path) if video else None)
        await safe_delete(processing)

import logging
from typing import List

from aiogram import F, Router
from aiogram.types import Message
from aiogram.utils.i18n import gettext as _

from core.config import config
from filters.common import SocialUrlFilter
from keyboard.inline import VideoRecognizeKeyboard
from services.media_downloader import FileTooLargeError, as_input_file, discard, remember_video_source, video_meta
from services.social_api import SocialAPI, SocialMedia
from utils.helpers import safe_delete
from utils.helpers.media_errors import file_too_large_text

router = Router()
logger = logging.getLogger(__name__)

UPLOAD_TIMEOUT: int = 300


def _caption() -> str:
    return _("Find any music you want quickly and easily via %(username_bot)s!") % dict(
        username_bot=config.telegram_username,
    )


@router.message(F.text, SocialUrlFilter())
async def social_handler(message: Message, social_platform: str, social_url: str) -> None:
    processing = await message.answer(text=_("Processing..."))
    media: List[SocialMedia] = []
    try:
        media = await SocialAPI.fetch(url=social_url, platform=social_platform)
        if not media:
            await message.answer(text=_("Could not fetch the video."))
            return
        for item in media:
            if item.kind == "video":
                sent = await message.answer_video(
                    video=as_input_file(str(item.path), timeout=UPLOAD_TIMEOUT),
                    supports_streaming=True,
                    **await video_meta(str(item.path)),
                    caption=_caption(),
                    reply_markup=VideoRecognizeKeyboard.make(),
                )
                await remember_video_source(sent, social_url)
            else:
                await message.answer_photo(photo=as_input_file(str(item.path), timeout=UPLOAD_TIMEOUT), caption=_caption())
    except FileTooLargeError:
        await message.answer(text=file_too_large_text())
    except Exception:
        logger.exception("%s download failed for %s", social_platform, social_url)
        await message.answer(text=_("Could not fetch the video."))
    finally:
        discard(*(str(item.path) for item in media))
        await safe_delete(processing)

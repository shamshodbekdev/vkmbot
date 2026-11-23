from contextlib import suppress
import logging

from aiogram import Router, F, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery
from aiogram.utils.i18n import gettext as _

from filters.callback import VideoRecognizeCallback
from keyboard.inline import VideoRecognizeKeyboard
from utils.helpers import recognize_media, safe_delete
from utils.constants import MAX_FILE_SIZE, MIN_DURATION

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(VideoRecognizeCallback.filter(F.action == "recognize"))
async def video_recognize_callback_handler(
    callback: CallbackQuery,
    bot: Bot,
) -> None:
    video = callback.message.video if callback.message else None
    if video is None:
        await callback.answer(_("Song not recognized."), show_alert=True)
        return

    await callback.answer()
    with suppress(TelegramBadRequest):
        await callback.message.edit_reply_markup(reply_markup=VideoRecognizeKeyboard.close_only())

    if callback.message.video.file_size and callback.message.video.file_size > MAX_FILE_SIZE:
        await callback.message.answer(text=_("File is too large. Maximum size is 10MB."))
        return

    if callback.message.video.duration is not None and callback.message.video.duration < MIN_DURATION:
        await callback.message.answer(text=_("Video is too short. Minimum duration is 2 seconds."))
        return

    processing = await callback.message.reply(text=_("Processing..."))
    try:
        result = await recognize_media(
            bot=bot,
            file_id=callback.message.video.file_id,
            filename="video.mp4",
        )
    except Exception:
        logger.exception("Video recognition failed")
        result = None
    finally:
        await safe_delete(processing)

    if not result:
        await callback.message.reply(text=_("Song not recognized."))
        return

    if result.coverart:
        await callback.message.reply_photo(
            photo=result.coverart,
            caption=result.text,
            reply_markup=result.keyboard,
        )
    else:
        await callback.message.reply(
            text=result.text,
            reply_markup=result.keyboard,
        )


@router.callback_query(VideoRecognizeCallback.filter(F.action == "close"))
async def video_recognize_close_handler(
    callback: CallbackQuery,
) -> None:
    with suppress(TelegramBadRequest):
        await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer()

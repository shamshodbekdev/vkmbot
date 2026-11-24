import logging

from aiogram import Bot, F, Router
from aiogram.types import Message
from aiogram.utils.i18n import gettext as _

from filters.common import OnlyPrivate

from utils.constants import MAX_FILE_SIZE, MAX_FILE_SIZE_MB, MIN_DURATION
from utils.helpers import recognize_media, safe_delete

router = Router()
logger = logging.getLogger(__name__)


# Private chats only: in groups every posted audio would be analysed and answered.
# (In groups the "recognize" button under videos the bot sends still works.)
@router.message(F.audio, OnlyPrivate())
async def audio_recognize_handler(message: Message, bot: Bot) -> None:
    if message.audio.file_size and message.audio.file_size > MAX_FILE_SIZE:
        await message.answer(text=_("File is too large. Maximum size is %(limit)sMB.") % dict(limit=MAX_FILE_SIZE_MB))
        return

    if message.audio.duration is not None and message.audio.duration < MIN_DURATION:
        await message.answer(text=_("Audio is too short. Minimum duration is 2 seconds."))
        return

    processing = await message.answer(text=_("Processing..."))
    try:
        result = await recognize_media(
            bot=bot,
            file_id=message.audio.file_id,
            filename=message.audio.file_name or "audio.mp3",
        )
    except Exception:
        logger.exception("Audio recognition failed")
        result = None
    finally:
        await safe_delete(processing)

    if not result:
        await message.answer(text=_("Song not recognized."))
        return

    if result.coverart:
        await message.answer_photo(photo=result.coverart, caption=result.text, reply_markup=result.keyboard)
    else:
        await message.answer(text=result.text, reply_markup=result.keyboard)

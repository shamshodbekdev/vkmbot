import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.utils.i18n import gettext as _

from filters.common import OnlyPrivate

from keyboard.inline import TranscriptionLanguageKeyboard
from states import TranscriptionState
from utils.constants import MAX_FILE_SIZE, MAX_FILE_SIZE_MB, MIN_DURATION
from utils.helpers import recognize_media, safe_delete

router = Router()
logger = logging.getLogger(__name__)


# Private chats only: in groups every posted voice would be analysed and answered.
# (In groups the "recognize" button under videos the bot sends still works.)
@router.message(F.voice, OnlyPrivate())
async def voice_recognize_handler(message: Message, bot: Bot, state: FSMContext) -> None:
    if message.voice.file_size and message.voice.file_size > MAX_FILE_SIZE:
        await message.answer(text=_("File is too large. Maximum size is %(limit)sMB.") % dict(limit=MAX_FILE_SIZE_MB))
        return

    if message.voice.duration is not None and message.voice.duration < MIN_DURATION:
        await message.answer(text=_("Audio is too short. Minimum duration is 2 seconds."))
        return

    processing = await message.answer(text=_("Processing..."))
    try:
        result = await recognize_media(bot=bot, file_id=message.voice.file_id, filename="audio.mp3")
    except Exception:
        logger.exception("Voice recognition failed")
        result = None
    finally:
        await safe_delete(processing)

    if not result:
        await state.set_state(TranscriptionState.WAITING_FOR_LANGUAGE)
        await state.update_data(file_id=message.voice.file_id, filename="audio.mp3")
        await message.answer(
            text=_("Song not recognized. Select a language to transcribe:"),
            reply_markup=TranscriptionLanguageKeyboard.make(),
        )
        return

    if result.coverart:
        await message.answer_photo(photo=result.coverart, caption=result.text, reply_markup=result.keyboard)
    else:
        await message.answer(text=result.text, reply_markup=result.keyboard)

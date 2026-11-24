import logging
from html import escape

from aiogram import Bot, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from aiogram.utils.i18n import gettext as _
from aiogram.utils.keyboard import InlineKeyboardBuilder

from filters.callback import TranscriptionLanguageCallback, YoutubeDownloadCallback
from services.transcription import Transcription
from services.youtube.search import YouTubeSearch
from states import TranscriptionState
from utils.constants import LOCALES, TRANSRIPTION_RESULT_COUNT
from services.transcription_api import MAX_AUDIO_SECONDS as TRANSCRIPTION_MAX_SECONDS
from utils.helpers import download_audio_sample, safe_delete

router = Router()
logger = logging.getLogger(__name__)

_LOCALE_CODES = {code for code, _label in LOCALES}
MAX_TRANSCRIPTION_TEXT: int = 3500


@router.callback_query(TranscriptionLanguageCallback.filter(), TranscriptionState.WAITING_FOR_LANGUAGE)
async def transcription_language_callback_handler(
    callback: CallbackQuery,
    callback_data: TranscriptionLanguageCallback,
    state: FSMContext,
    bot: Bot,
) -> None:
    data = await state.get_data()
    await state.set_state(None)

    file_id = data.get("file_id")
    filename = data.get("filename", "audio.mp3")
    if not file_id or callback_data.locale not in _LOCALE_CODES:
        await callback.answer()
        return

    await callback.answer()
    await safe_delete(callback.message)
    processing = await callback.message.answer(text=_("Processing..."))
    try:
        audio_bytes = await download_audio_sample(bot, file_id, TRANSCRIPTION_MAX_SECONDS)
        result = None if not audio_bytes else await Transcription.transcribe(
            file=audio_bytes,
            filename=filename,
            language=callback_data.locale,
        )

        if not result or not result.text.strip():
            await callback.message.answer(text=_("Could not transcribe the audio."))
            return

        query = result.text.strip()
        await callback.message.answer(text=escape(query[:MAX_TRANSCRIPTION_TEXT]))

        songs = [song for song in await YouTubeSearch.search(query=query, limit=TRANSRIPTION_RESULT_COUNT, fallback=True) if song.videoId]
        if not songs:
            await callback.message.answer(text=_("No results found for the transcription."))
            return

        lines = []
        keyboard = InlineKeyboardBuilder()
        for i, song in enumerate(songs):
            artists = ", ".join(a.name for a in song.artists)
            lines.append(
                "%(num)s. %(title)s – %(artists)s" % dict(num=i + 1, title=escape(song.title), artists=escape(artists))
            )
            keyboard.button(
                text=str(i + 1),
                callback_data=YoutubeDownloadCallback(video_id=song.videoId).pack(),
            )
        keyboard.adjust(5)
        await callback.message.answer(text="\n".join(lines), reply_markup=keyboard.as_markup())
    except Exception:
        logger.exception("Transcription failed")
        await callback.message.answer(text=_("Could not transcribe the audio."))
    finally:
        await safe_delete(processing)

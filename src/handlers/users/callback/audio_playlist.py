import logging
import re
from contextlib import suppress
from pathlib import Path
from typing import Optional

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import BufferedInputFile, CallbackQuery, FSInputFile, InputFile
from aiogram.utils.i18n import gettext as _

from core.config import config
from database.models import AudioPlaylist, User, UserPreferences, YoutubeAudio
from filters.callback.audio_playlist import AudioPlaylistCallback
from keyboard.inline.audio_download import AudioDownloadKeyboard
from services.media_downloader import discard
from services.youtube_api import YouTubeAPI
from utils.helpers import download_file_bytes, safe_delete

router = Router()
logger = logging.getLogger(__name__)

# getFile on api.telegram.org only serves files up to 20 MB.
BOT_API_DOWNLOAD_LIMIT: int = 20 * 1024 * 1024
_UNSAFE_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|\r\n\t]+')


async def _refresh_keyboard(callback: CallbackQuery, video_id: str, user: User, liked: bool) -> None:
    """Flip ❤️ <-> 💔 on the message the button belongs to."""
    prefs, __ = await UserPreferences.get_or_create(user=user)
    with suppress(TelegramBadRequest):
        await callback.message.edit_reply_markup(
            reply_markup=AudioDownloadKeyboard.make(video_id=video_id, like_buttons=prefs.like_buttons, liked=liked),
        )


@router.callback_query(AudioPlaylistCallback.filter(F.action == "like"))
async def audio_playlist_like_handler(
    callback: CallbackQuery,
    callback_data: AudioPlaylistCallback,
    user: User,
) -> None:
    audio = await YoutubeAudio.get_or_none(video_id=callback_data.video_id)
    if not audio:
        await callback.answer(_("Track not found."), show_alert=True)
        return
    await AudioPlaylist.get_or_create(user=user, audio=audio)
    await callback.answer(_("Saved to playlist"), show_alert=False)
    await _refresh_keyboard(callback, callback_data.video_id, user, liked=True)


@router.callback_query(AudioPlaylistCallback.filter(F.action == "unlike"))
async def audio_playlist_unlike_handler(
    callback: CallbackQuery,
    callback_data: AudioPlaylistCallback,
    user: User,
) -> None:
    audio = await YoutubeAudio.filter(video_id=callback_data.video_id).first()
    if audio:
        await AudioPlaylist.filter(user=user, audio=audio).delete()
    await callback.answer(_("Removed from playlist"), show_alert=False)
    await _refresh_keyboard(callback, callback_data.video_id, user, liked=False)


def _file_name(audio_title: Optional[str], performer: Optional[str], extension: str) -> str:
    title = audio_title or "audio"
    if performer and not title.startswith(performer):
        title = "%s - %s" % (performer, title)
    return "%s%s" % (_UNSAFE_FILENAME_CHARS.sub(" ", title).strip()[:120] or "audio", extension)


@router.callback_query(AudioPlaylistCallback.filter(F.action == "file"))
async def audio_playlist_file_handler(callback: CallbackQuery, callback_data: AudioPlaylistCallback, bot: Bot) -> None:
    """💾: send the track as a document, so it can be saved to the device."""
    audio = callback.message.audio if callback.message else None
    await callback.answer(_("Downloading..."))
    document: Optional[InputFile] = None
    downloaded: Optional[Path] = None
    try:
        if audio and (config.telegram_api_local or (audio.file_size or 0) <= BOT_API_DOWNLOAD_LIMIT):
            extension = Path(audio.file_name or "").suffix or ".m4a"
            with suppress(Exception):
                data = await download_file_bytes(bot, audio.file_id)
                document = BufferedInputFile(data, filename=_file_name(audio.title, audio.performer, extension))
        if document is None:
            media = await YouTubeAPI.download_audio(callback_data.video_id)
            if media:
                downloaded = media.path
                title = audio.title if audio else media.title
                performer = audio.performer if audio else None
                document = FSInputFile(media.path, filename=_file_name(title, performer, media.path.suffix))
        if document is None:
            await callback.message.answer(text=_("Download failed."))
            return
        await callback.message.answer_document(document=document)
    except Exception:
        logger.exception("Sending track %s as a file failed", callback_data.video_id)
        await callback.message.answer(text=_("Download failed."))
    finally:
        discard(str(downloaded) if downloaded else None)


@router.callback_query(AudioPlaylistCallback.filter(F.action == "close"))
async def audio_playlist_close_handler(callback: CallbackQuery) -> None:
    await safe_delete(callback.message)
    await callback.answer()

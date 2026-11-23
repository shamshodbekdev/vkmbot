import asyncio
import logging
import re
from typing import Optional

from aiogram.exceptions import TelegramRetryAfter
from aiogram.types import InlineKeyboardMarkup, Message
from aiogram.utils.i18n import gettext as _

from core.config import config
from database.models import YoutubeAudio
from keyboard.inline import AudioDownloadKeyboard
from services.media_downloader import as_input_file, discard
from services.youtube.download import YouTubeDownload
from services.youtube.song import YouTubeSong
from utils.constants.youtube import MAX_AUDIO_META_LENGTH

logger = logging.getLogger(__name__)

AUDIO_UPLOAD_TIMEOUT: int = 300
_UNSAFE_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|\r\n\t]+')


def _caption() -> str:
    return _("Find any music you want quickly and easily via %(username_bot)s!") % dict(
        username_bot=config.telegram_username,
    )


def _filename(title: str) -> str:
    name = _UNSAFE_FILENAME_CHARS.sub(" ", title).strip()[:120]
    return "%s.mp3" % (name or "audio")


async def _with_retry(coro_factory):
    while True:
        try:
            return await coro_factory()
        except TelegramRetryAfter as error:
            await asyncio.sleep(error.retry_after + 1)


class YouTubeAudioSender:
    """Sends a YouTube track as audio, reusing Telegram's file_id when cached."""

    @staticmethod
    async def send(target: Message, video_id: str, like_buttons: bool) -> bool:
        """Send the track into ``target``'s chat. Returns False if it could not be downloaded."""
        reply_markup: Optional[InlineKeyboardMarkup] = (
            AudioDownloadKeyboard.make(video_id=video_id) if like_buttons else None
        )

        cached = await YoutubeAudio.get_or_none(video_id=video_id)
        if cached:
            await _with_retry(lambda: target.answer_audio(
                audio=cached.file_id,
                caption=_caption(),
                reply_markup=reply_markup,
            ))
            return True

        song_detail = await YouTubeSong.get(video_id=video_id)
        video_details = song_detail.videoDetails if song_detail else None
        download = await YouTubeDownload.get(video_id=video_id)
        if not download or not download.link:
            return False

        title = ((video_details.title if video_details else "") or download.title)[:MAX_AUDIO_META_LENGTH]
        performer = (video_details.author if video_details else "")[:MAX_AUDIO_META_LENGTH]
        duration = int(download.duration)

        try:
            result = await _with_retry(lambda: target.answer_audio(
                audio=as_input_file(download.link, filename=_filename(title), timeout=AUDIO_UPLOAD_TIMEOUT),
                title=title or None,
                performer=performer or None,
                duration=duration or None,
                caption=_caption(),
                reply_markup=reply_markup,
            ))
        finally:
            discard(download.link)

        if result.audio:
            # get_or_create: another user may have downloaded the same track meanwhile.
            await YoutubeAudio.get_or_create(
                video_id=video_id,
                defaults=dict(
                    file_id=result.audio.file_id,
                    title=title,
                    performer=performer,
                    duration=duration,
                    filesize=download.filesize,
                ),
            )
        return True

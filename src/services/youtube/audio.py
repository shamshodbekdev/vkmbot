import asyncio
import logging
import os
import re
from typing import Optional

from aiogram.exceptions import TelegramRetryAfter
from aiogram.types import FSInputFile, InlineKeyboardMarkup, Message
from aiogram.utils.i18n import gettext as _

from core.config import config
from database.models import YoutubeAudio
from keyboard.inline import AudioDownloadKeyboard
from services.media_downloader import as_input_file, discard
from services.youtube.download import YouTubeDownload
from services.youtube.song import YouTubeSong
from services.youtube_api import YouTubeAPI
from utils.constants.youtube import MAX_AUDIO_META_LENGTH

logger = logging.getLogger(__name__)

AUDIO_UPLOAD_TIMEOUT: int = 300
_UNSAFE_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|\r\n\t]+')


def _caption() -> str:
    return _("Find any music you want quickly and easily via %(username_bot)s!") % dict(
        username_bot=config.telegram_username,
    )


def _filename(title: str, source: str = "") -> str:
    name = _UNSAFE_FILENAME_CHARS.sub(" ", title).strip()[:120]
    extension = os.path.splitext(source)[1].lower() or ".m4a"
    return "%s%s" % (name or "audio", extension)


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
        reply_markup: Optional[InlineKeyboardMarkup] = AudioDownloadKeyboard.make(
            video_id=video_id, like_buttons=like_buttons,
        )

        cached = await YoutubeAudio.get_or_none(video_id=video_id)
        if cached:
            await _with_retry(lambda: target.answer_audio(
                audio=cached.file_id,
                caption=_caption(),
                reply_markup=reply_markup,
            ))
            return True

        # Metadata, file and cover are independent: fetch them in parallel.
        song_detail, download, thumb = await asyncio.gather(
            YouTubeSong.get(video_id=video_id),
            YouTubeDownload.get(video_id=video_id),
            YouTubeAPI.thumbnail_file(video_id),
        )
        video_details = song_detail.videoDetails if song_detail else None
        if not download or not download.link:
            discard(str(thumb) if thumb else None)
            return False

        title = ((video_details.title if video_details else "") or download.title)[:MAX_AUDIO_META_LENGTH]
        performer = (video_details.author if video_details else "")[:MAX_AUDIO_META_LENGTH]
        duration = int(download.duration)
        # Shown in Telegram as "Artist - Title"; the DB keeps both parts separately.
        display_title = (
            "%s - %s" % (performer, title) if performer and not title.lower().startswith(performer.lower()) else title
        )[:MAX_AUDIO_META_LENGTH]

        try:
            result = await _with_retry(lambda: target.answer_audio(
                audio=as_input_file(download.link, filename=_filename(display_title, download.link), timeout=AUDIO_UPLOAD_TIMEOUT),
                thumbnail=FSInputFile(thumb) if thumb else None,
                title=display_title or None,
                performer=performer or None,
                duration=duration or None,
                caption=_caption(),
                reply_markup=reply_markup,
            ))
        finally:
            discard(download.link, str(thumb) if thumb else None)

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

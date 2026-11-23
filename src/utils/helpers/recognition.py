from dataclasses import dataclass
from html import escape
from typing import Optional

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from services.shazam.recognize import Shazam
from services.youtube.search import YouTubeSearch
from filters.callback.youtube_download import YoutubeDownloadCallback
from utils.constants import RECOGNITION_SEARCH_LIMIT
from utils.helpers.telegram import download_file_bytes


@dataclass
class RecognitionResult:
    text: str
    coverart: Optional[str]
    keyboard: InlineKeyboardMarkup


async def recognize_media(
    bot: Bot,
    file_id: str,
    filename: str,
) -> Optional[RecognitionResult]:
    audio_bytes = await download_file_bytes(bot, file_id)

    result = await Shazam.recognize(file=audio_bytes, filename=filename)

    if not result or not result.matches or not result.track:
        return None

    subject = result.track.share.subject if result.track.share else None
    if not subject:
        return None

    songs = await YouTubeSearch.search(query=subject, limit=RECOGNITION_SEARCH_LIMIT)

    lines = ["<i>%(subject)s</i>\n" % dict(subject=escape(subject))]
    keyboard = InlineKeyboardBuilder()

    for i, song in enumerate(song for song in songs if song.videoId):
        artists = ", ".join(a.name for a in song.artists)
        lines.append(
            "%(num)s. %(title)s – %(artists)s" % dict(num=i + 1, title=escape(song.title), artists=escape(artists))
        )
        keyboard.button(
            text=str(i + 1),
            callback_data=YoutubeDownloadCallback(video_id=song.videoId).pack(),
        )

    keyboard.adjust(5)

    return RecognitionResult(
        text="\n".join(lines),
        coverart=result.track.images.coverart if result.track.images else None,
        keyboard=keyboard.as_markup(),
    )

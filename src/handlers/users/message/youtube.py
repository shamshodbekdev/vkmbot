import logging
from html import escape

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message, URLInputFile
from aiogram.utils.i18n import gettext as _

from filters.common import YouTubeUrlFilter
from keyboard.inline.youtube_link import YoutubeLinkKeyboard
from services.youtube_api import VideoInfo, YouTubeAPI, fallback_thumbnail
from utils.helpers import safe_delete

router = Router()
logger = logging.getLogger(__name__)


def preview_caption(info: VideoInfo) -> str:
    lines = ["<b>%s</b>" % escape(info.title)]
    details = []
    if info.uploader:
        details.append("👤 %s" % escape(info.uploader))
    if info.duration:
        minutes, seconds = divmod(info.duration, 60)
        hours, minutes = divmod(minutes, 60)
        details.append("⏱ %s" % ("%d:%02d:%02d" % (hours, minutes, seconds) if hours else "%d:%02d" % (minutes, seconds)))
    if details:
        lines.append(" · ".join(details))
    return "\n".join(lines)


@router.message(F.text, YouTubeUrlFilter())
async def youtube_handler(message: Message, youtube_url: str) -> None:
    """Show the video's cover with "📼 Video" / "🎧 Audio" buttons; the download starts on a click."""
    processing = await message.answer(text=_("Processing..."))
    try:
        info = await YouTubeAPI.info(youtube_url)
        if not info:
            await message.answer(text=_("Could not fetch the video."))
            return
        keyboard = YoutubeLinkKeyboard.make(info.video_id, info.qualities)
        for cover in dict.fromkeys((info.thumbnail_url, fallback_thumbnail(info.video_id))):
            try:
                await message.answer_photo(
                    photo=URLInputFile(cover, filename="%s.jpg" % info.video_id, timeout=30),
                    caption=preview_caption(info),
                    reply_markup=keyboard,
                )
                return
            except TelegramBadRequest as error:
                logger.info("Cover %s for %s not sent (%s)", cover, info.video_id, error)
        # No usable cover: still let the user choose.
        await message.answer(text=preview_caption(info), reply_markup=keyboard)
    except Exception:
        logger.exception("YouTube preview failed for %s", youtube_url)
        await message.answer(text=_("Could not fetch the video."))
    finally:
        await safe_delete(processing)

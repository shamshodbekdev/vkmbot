import logging

from aiogram import Router
from aiogram.types import CallbackQuery
from aiogram.utils.i18n import gettext as _

from database.models import User, UserPreferences, YoutubeAudio
from filters.callback import YoutubeDownloadCallback
from services.youtube.audio import YouTubeAudioSender

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(YoutubeDownloadCallback.filter())
async def youtube_download_callback_handler(
    callback: CallbackQuery,
    callback_data: YoutubeDownloadCallback,
    user: User,
) -> None:
    video_id = callback_data.video_id
    prefs, __ = await UserPreferences.get_or_create(user=user)

    if await YoutubeAudio.exists(video_id=video_id):
        await callback.answer()
    else:
        await callback.answer(_("Downloading..."))

    try:
        sent = await YouTubeAudioSender.send(
            target=callback.message,
            video_id=video_id,
            like_buttons=prefs.like_buttons,
        )
    except Exception:
        logger.exception("Audio download failed for %s", video_id)
        sent = False

    if not sent:
        await callback.message.answer(text=_("Download failed."))

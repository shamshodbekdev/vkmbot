import logging

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from aiogram.utils.i18n import gettext as _

from database.models import User, UserPreferences
from filters.callback.bulk_download import BulkDownloadCallback
from services.youtube.audio import YouTubeAudioSender

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(BulkDownloadCallback.filter())
async def bulk_download_callback_handler(
    callback: CallbackQuery,
    state: FSMContext,
    user: User,
) -> None:
    data = await state.get_data()
    video_ids = [video_id for video_id in data.get("bulk_video_ids", []) if video_id]

    if not video_ids:
        await callback.answer(_("Nothing to download."))
        return

    await callback.answer(_("Downloading..."))

    prefs, __ = await UserPreferences.get_or_create(user=user)
    for video_id in video_ids:
        try:
            await YouTubeAudioSender.send(
                target=callback.message,
                video_id=video_id,
                like_buttons=prefs.like_buttons,
            )
        except Exception:
            logger.exception("Bulk download failed for %s", video_id)

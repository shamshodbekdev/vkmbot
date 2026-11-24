from aiogram import F, Router
from aiogram.types import BufferedInputFile, CallbackQuery

from filters.callback.reload import ReloadCallback
from filters.common import IsModerator
from keyboard.inline.reload import ReloadKeyboard
from services.admin_panel_cache import analytics_panel, statistics_panel
from utils.helpers.telegram import safe_delete

router = Router()


@router.callback_query(ReloadCallback.filter(F.action == "statistics"), IsModerator())
async def reload_statistics_callback(callback: CallbackQuery) -> None:
    caption, image = await statistics_panel(force=True)
    await callback.message.answer_photo(
        photo=BufferedInputFile(image, filename="statistics.png"),
        caption=caption,
        reply_markup=ReloadKeyboard.statistics(),
    )
    await safe_delete(callback.message)
    await callback.answer()


@router.callback_query(ReloadCallback.filter(F.action == "analytics"), IsModerator())
async def reload_analytics_callback(callback: CallbackQuery) -> None:
    caption, image = await analytics_panel(force=True)
    await callback.message.answer_photo(
        photo=BufferedInputFile(image, filename="analytics.png"),
        caption=caption,
        reply_markup=ReloadKeyboard.analytics(),
    )
    await safe_delete(callback.message)
    await callback.answer()

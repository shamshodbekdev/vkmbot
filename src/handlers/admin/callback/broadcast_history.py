from contextlib import suppress
from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery
from aiogram.utils.i18n import gettext as _
from filters.common import IsAdmin
from filters.callback.broadcast_history import BroadcastHistoryCallback
from keyboard.inline.broadcast_history import BroadcastHistoryKeyboard
from utils.constants.broadcast import BROADCAST_PAGE_SIZE as PAGE_SIZE
from database.models.broadcast import BroadcastRecord
from utils.formatters import build_record_detail, build_broadcast_list

router = Router()


@router.callback_query(BroadcastHistoryCallback.filter(F.action == "menu"), IsAdmin())
async def broadcast_menu_callback(callback: CallbackQuery) -> None:
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=_("<b>Broadcast</b>\n\nSelect an action."),
            reply_markup=BroadcastHistoryKeyboard.menu(),
        )
    await callback.answer()


@router.callback_query(BroadcastHistoryCallback.filter(F.action == "list"), IsAdmin())
async def broadcast_history_list_callback(
    callback: CallbackQuery,
    callback_data: BroadcastHistoryCallback,
) -> None:
    page = callback_data.page or 0
    total = await BroadcastRecord.all().count()
    records = await BroadcastRecord.all().order_by("-created_at").offset(page * PAGE_SIZE).limit(PAGE_SIZE)
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=build_broadcast_list(total),
            reply_markup=BroadcastHistoryKeyboard.list(records, page, total),
        )
    await callback.answer()


@router.callback_query(BroadcastHistoryCallback.filter(F.action == "select"), IsAdmin())
async def broadcast_history_select_callback(
    callback: CallbackQuery,
    callback_data: BroadcastHistoryCallback,
) -> None:
    record = await BroadcastRecord.get_or_none(id=callback_data.broadcast_id)
    if not record:
        await callback.answer(_("Broadcast not found."), show_alert=True)
        return
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=build_record_detail(record),
            reply_markup=BroadcastHistoryKeyboard.detail(str(record.id), callback_data.page or 0),
        )
    await callback.answer()


@router.callback_query(BroadcastHistoryCallback.filter(F.action == "noop"), IsAdmin())
async def broadcast_history_noop_callback(callback: CallbackQuery) -> None:
    await callback.answer()

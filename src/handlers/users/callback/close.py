from aiogram import Router
from aiogram.types import CallbackQuery

from filters.callback.close import CloseCallback
from utils.helpers import safe_delete

router = Router()


@router.callback_query(CloseCallback.filter())
async def close_callback_handler(callback: CallbackQuery) -> None:
    await safe_delete(callback.message)
    await callback.answer()

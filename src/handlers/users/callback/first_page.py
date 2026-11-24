from aiogram import Router
from aiogram.types import CallbackQuery
from aiogram.utils.i18n import gettext as _

from filters.callback.first_page import FirstPageCallback

router = Router()


@router.callback_query(FirstPageCallback.filter())
async def first_page_callback_handler(callback: CallbackQuery) -> None:
    await callback.answer(_("You are on the first page"))

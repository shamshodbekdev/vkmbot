from aiogram import Router
from aiogram.types import CallbackQuery
from aiogram.utils.i18n import gettext as _

router = Router()


@router.callback_query()
async def stale_callback_handler(callback: CallbackQuery) -> None:
    """Answer buttons nobody handled (e.g. from an expired step) so the client stops loading."""
    await callback.answer(_("This button is no longer active."), show_alert=False)

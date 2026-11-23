from html import escape

from aiogram import Bot, Router, F
from aiogram.types import CallbackQuery
from humanize import intcomma
from aiogram.fsm.context import FSMContext
from aiogram.utils.i18n import gettext as _
from keyboard.reply import BackKeyboard
from keyboard.inline import ManageAdminKeyboard
from filters.callback import AdminCallback
from states.admin import ManageAdminState
from filters.common import IsAdmin
from database.enums import UserRole
from database.models import User
from utils.formatters import build_admin_detail, build_admins_list
from core.commands import Commands
from core.config import config

router = Router()

@router.callback_query(AdminCallback.filter(F.action == "list"), IsAdmin())
async def admin_list_callback(callback: CallbackQuery) -> None:
    total = await User.filter(role=UserRole.ADMINISTRATOR).count()
    await callback.message.edit_text(
        text=build_admins_list(intcomma(total)),
        reply_markup=await ManageAdminKeyboard.list()
    )
    await callback.answer()

@router.callback_query(AdminCallback.filter(F.action == "select"), IsAdmin())
async def admin_select_callback(callback: CallbackQuery, callback_data: AdminCallback) -> None:
    user = await User.get_or_none(telegram_id=callback_data.admin_id)
    if not user:
        await callback.answer(_("Admin not found."), show_alert=True)
        return

    await callback.message.edit_text(
        text=build_admin_detail(user),
        reply_markup=ManageAdminKeyboard.detail(callback_data.admin_id)
    )
    await callback.answer()

@router.callback_query(AdminCallback.filter(F.action == "confirm_delete"), IsAdmin())
async def admin_confirm_delete_callback(callback: CallbackQuery, callback_data: AdminCallback) -> None:
    user = await User.get_or_none(telegram_id=callback_data.admin_id)
    display = escape(user.display_name) if user else str(callback_data.admin_id)
    await callback.message.edit_text(
        text=_("Are you sure you want to remove <b>%(name)s</b> from admins?") % dict(name=display),
        reply_markup=ManageAdminKeyboard.confirm_delete(callback_data.admin_id)
    )
    await callback.answer()


@router.callback_query(AdminCallback.filter(F.action == "do_delete"), IsAdmin())
async def admin_do_delete_callback(callback: CallbackQuery, callback_data: AdminCallback, bot: Bot) -> None:
    user = await User.get_or_none(telegram_id=callback_data.admin_id)
    if user:
        user.role = UserRole.USER
        await user.save()
        if user.telegram_id != config.telegram_id:
            await Commands.remove_admin_commands(bot, user.telegram_id)

    total = await User.filter(role=UserRole.ADMINISTRATOR).count()
    await callback.message.edit_text(
        text=build_admins_list(intcomma(total)),
        reply_markup=await ManageAdminKeyboard.list()
    )
    await callback.answer(_("Admin has been removed successfully."))


@router.callback_query(AdminCallback.filter(F.action == "do_add"), IsAdmin())
async def admin_do_add_callback(callback: CallbackQuery, callback_data: AdminCallback, bot: Bot) -> None:
    user = await User.get_or_none(telegram_id=callback_data.admin_id)
    if user is None:
        await callback.answer(_("User not found."), show_alert=True)
        return

    user.role = UserRole.ADMINISTRATOR
    await user.save()
    await Commands.set_admin_commands(bot, user.telegram_id)

    total = await User.filter(role=UserRole.ADMINISTRATOR).count()
    await callback.message.edit_text(
        text=build_admins_list(intcomma(total)),
        reply_markup=await ManageAdminKeyboard.list()
    )
    await callback.answer(_("User has been made an admin successfully."))

@router.callback_query(AdminCallback.filter(F.action == "add"), IsAdmin())
async def admin_add_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.answer(
        text=_("Please, send a chat id of the user you want to make an admin."),
        reply_markup=BackKeyboard.make()
    )
    await state.set_state(ManageAdminState.WAITING_FOR_CHAT_ID)
    await callback.answer()

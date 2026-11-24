from html import escape

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.utils.i18n import lazy_gettext as __, gettext as _
from keyboard.reply import ManageKeyboard, BackKeyboard
from keyboard.inline import ManageAdminKeyboard
from utils.formatters import build_admins_list
from states.admin import ManageAdminState
from filters.common import IsSuperAdmin
from database.enums import STAFF_ROLES, UserRole
from core.config import config
from database.models import User
from humanize import intcomma

router = Router()

@router.message(F.text == __("Admins"), IsSuperAdmin())
async def manage_admins_handler(message: Message, state: FSMContext) -> None:
    total = await User.filter(role__in=STAFF_ROLES).count()
    await message.answer(
        text=build_admins_list(intcomma(total)),
        reply_markup=await ManageAdminKeyboard.list()
    )
    await state.clear()

@router.message(F.text == "⬅️", StateFilter(ManageAdminState.WAITING_FOR_CHAT_ID), IsSuperAdmin())
async def manage_admins_add_back_handler(message: Message, state: FSMContext) -> None:
    total = await User.filter(role__in=STAFF_ROLES).count()
    await message.answer(text=_("Main menu"), reply_markup=ManageKeyboard.make())
    await message.answer(text=build_admins_list(intcomma(total)), reply_markup=await ManageAdminKeyboard.list())
    await state.clear()

@router.message(StateFilter(ManageAdminState.WAITING_FOR_CHAT_ID), IsSuperAdmin())
async def manage_admins_chat_id_handler(message: Message, state: FSMContext) -> None:
    chat_id = message.text.strip() if message.text else ""
    if not chat_id.isdigit():
        await message.answer(
            text=_("Chat id must be a number. Please, try again."),
            reply_markup=BackKeyboard.make()
        )
        return

    user = await User.get_or_none(telegram_id=int(chat_id))
    if user is None:
        await message.answer(
            text=_("User with this chat id not found. Please, try again."),
            reply_markup=BackKeyboard.make()
        )
        return

    if user.role in STAFF_ROLES or user.telegram_id == config.telegram_id:
        await message.answer(
            text=_("User is already an admin."),
            reply_markup=BackKeyboard.make()
        )
        return

    await message.answer(text=_("Main menu"), reply_markup=ManageKeyboard.make())
    await message.answer(
        text=_("Which role should <b>%(name)s</b> get?") % dict(name=escape(user.display_name)),
        reply_markup=ManageAdminKeyboard.confirm_add(int(chat_id)),
    )
    await state.clear()
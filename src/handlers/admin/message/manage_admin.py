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
from filters.common import IsAdmin
from database.enums import UserRole
from database.models import User
from humanize import intcomma

router = Router()

@router.message(F.text == __("Admins"), IsAdmin())
async def manage_admins_handler(message: Message, state: FSMContext) -> None:
    total = await User.filter(role=UserRole.ADMINISTRATOR).count()
    await message.answer(
        text=build_admins_list(intcomma(total)),
        reply_markup=await ManageAdminKeyboard.list()
    )
    await state.clear()

@router.message(F.text == "⬅️", StateFilter(ManageAdminState.WAITING_FOR_CHAT_ID), IsAdmin())
async def manage_admins_add_back_handler(message: Message, state: FSMContext) -> None:
    total = await User.filter(role=UserRole.ADMINISTRATOR).count()
    await message.answer(text=_("Main menu"), reply_markup=ManageKeyboard.make())
    await message.answer(text=build_admins_list(intcomma(total)), reply_markup=await ManageAdminKeyboard.list())
    await state.clear()

@router.message(StateFilter(ManageAdminState.WAITING_FOR_CHAT_ID), IsAdmin())
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

    if user.role == UserRole.ADMINISTRATOR:
        await message.answer(
            text=_("User is already an admin."),
            reply_markup=BackKeyboard.make()
        )
        return

    await message.answer(text=_("Main menu"), reply_markup=ManageKeyboard.make())
    await message.answer(
        text=_("Are you sure you want to make <b>%(name)s</b> an admin?") % dict(name=escape(user.display_name)),
        reply_markup=ManageAdminKeyboard.confirm_add(int(chat_id)),
    )
    await state.clear()
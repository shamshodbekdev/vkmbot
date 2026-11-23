from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.utils.i18n import lazy_gettext as __, gettext as _
from keyboard.reply import ManageKeyboard, BackKeyboard
from keyboard.inline import ManageUserKeyboard
from utils.helpers import is_temp_banned
from utils.formatters import build_user_detail, build_users_list
from states.admin import ManageUserState
from filters.common import IsAdmin
from database.models import User
from humanize import intcomma

router = Router()

@router.message(F.text == __("Users"), IsAdmin())
async def manage_users_handler(message: Message, state: FSMContext) -> None:
    total = await User.all().count()
    blocked = await User.filter(is_blocked=True).count()
    await message.answer(text=build_users_list(intcomma(total), intcomma(blocked)), reply_markup=BackKeyboard.make())
    await state.set_state(ManageUserState.WAITING_FOR_CHAT_ID)

@router.message(F.text == "⬅️", StateFilter(ManageUserState.WAITING_FOR_CHAT_ID), IsAdmin())
async def manage_users_back_handler(message: Message, state: FSMContext) -> None:
    await message.answer(text=_("Main menu"), reply_markup=ManageKeyboard.make())
    await state.clear()

@router.message(StateFilter(ManageUserState.WAITING_FOR_CHAT_ID), IsAdmin())
async def manage_users_chat_id_handler(message: Message, state: FSMContext) -> None:
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

    await state.clear()
    await message.answer(text=_("Main menu"), reply_markup=ManageKeyboard.make())
    await message.answer(
        text=build_user_detail(user),
        reply_markup=ManageUserKeyboard.detail(user.telegram_id, user.is_blocked, is_temp_banned(user)),
    )

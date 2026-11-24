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
from filters.common import IsModerator
from database.models import User
from humanize import intcomma
from html import escape

router = Router()

@router.message(F.text == __("Users"), IsModerator())
async def manage_users_handler(message: Message, state: FSMContext) -> None:
    total = await User.all().count()
    blocked = await User.filter(is_blocked=True).count()
    await message.answer(text=build_users_list(intcomma(total), intcomma(blocked)), reply_markup=BackKeyboard.make())
    await state.set_state(ManageUserState.WAITING_FOR_CHAT_ID)

@router.message(F.text == "⬅️", StateFilter(ManageUserState.WAITING_FOR_CHAT_ID), IsModerator())
async def manage_users_back_handler(message: Message, state: FSMContext) -> None:
    await message.answer(text=_("Main menu"), reply_markup=ManageKeyboard.make())
    await state.clear()

SEARCH_LIMIT: int = 10


@router.message(StateFilter(ManageUserState.WAITING_FOR_CHAT_ID), IsModerator())
async def manage_users_chat_id_handler(message: Message, state: FSMContext) -> None:
    chat_id = message.text.strip().lstrip("@") if message.text else ""
    if chat_id.lstrip("-").isdigit():
        user = await User.get_or_none(telegram_id=int(chat_id))
    elif len(chat_id) >= 2:
        # Search by name (display name of private chats / title of groups).
        found = await User.filter(display_name__icontains=chat_id).order_by("-updated_at").limit(SEARCH_LIMIT + 1)
        if not found:
            await message.answer(
                text=_("Nobody found for <b>%(query)s</b>. Send a Telegram ID or another name.") % dict(query=escape(chat_id)),
                reply_markup=BackKeyboard.make(),
            )
            return
        if len(found) == 1:
            user = found[0]
        else:
            await message.answer(
                text=_("<b>🔎 Found %(count)s</b> for <b>%(query)s</b>. Choose a person:") % dict(
                    count=("%d+" % SEARCH_LIMIT) if len(found) > SEARCH_LIMIT else len(found), query=escape(chat_id),
                ),
                reply_markup=ManageUserKeyboard.search_results(found[:SEARCH_LIMIT]),
            )
            return
    else:
        await message.answer(
            text=_("Send a Telegram ID (numbers) or at least 2 letters of a name."),
            reply_markup=BackKeyboard.make()
        )
        return
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

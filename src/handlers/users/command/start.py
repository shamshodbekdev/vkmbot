from aiogram import Router
from aiogram.enums import ChatType
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.utils.i18n import gettext as _

from keyboard.inline import LanguageKeyboard, StartKeyboard
from utils.constants import LANGUAGE_PROMPT
from utils.helpers import has_chosen_language

router = Router()


@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    # First visit in a private chat: choose a language before anything else.
    if (
        message.chat.type == ChatType.PRIVATE
        and message.from_user is not None
        and not await has_chosen_language(message.from_user.id)
    ):
        await message.answer(
            text=LANGUAGE_PROMPT,
            reply_markup=LanguageKeyboard.make(action="start", closable=False),
        )
        return
    await message.answer(
        text=_("Hello, world!"),
        reply_markup=StartKeyboard.make(),
    )

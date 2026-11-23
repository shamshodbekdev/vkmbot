from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.utils.i18n import gettext as _
from keyboard.inline import LanguageKeyboard
from database.models import User

router = Router()

@router.message(Command(commands=["language", "lang"]))
async def language_handler(message: Message, user: User) -> None:
    await message.answer(
        text=_("Choose your language:"),
        reply_markup=LanguageKeyboard.make(user.language_code)
    )
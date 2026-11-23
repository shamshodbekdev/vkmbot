from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.utils.i18n import gettext as _
from database.models import User, UserPreferences
from keyboard.inline import SettingsKeyboard

router = Router()


@router.message(Command("settings"))
async def settings_handler(message: Message, user: User) -> None:
    prefs, __ = await UserPreferences.get_or_create(user=user)
    await message.answer(
        text=_("<b>Settings</b>\n\nWhat would you like to change?"),
        reply_markup=SettingsKeyboard.make(
            language_code=user.language_code,
            max_results=prefs.max_results,
            like_buttons=prefs.like_buttons,
        ),
    )

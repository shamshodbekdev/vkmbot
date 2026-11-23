from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.utils.i18n import gettext as _
from services.youtube.mood import YouTubeMood
from keyboard.inline import MoodKeyboard

router = Router()


@router.message(Command("mood"))
async def mood_handler(message: Message) -> None:
    moods = await YouTubeMood.moods()
    if not moods:
        await message.answer(text=_("No moods available."))
        return
    await message.answer(
        text=_("Select a mood:"),
        reply_markup=MoodKeyboard.moods(moods=moods, page=0),
    )

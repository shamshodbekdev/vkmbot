from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.utils.i18n import gettext as _
from aiogram.fsm.context import FSMContext

from keyboard.inline import StartKeyboard

router = Router()

@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext) -> None:
    await message.answer(
        text=_("Hello, world!"),
        reply_markup=StartKeyboard.make(),
    )
    await state.clear()
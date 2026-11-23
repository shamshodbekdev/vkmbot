from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.utils.i18n import gettext as _
from keyboard.reply import ManageKeyboard
from filters.common import IsAdmin

router = Router()

@router.message(Command("manage"), IsAdmin())
async def manage_handler(message: Message, state: FSMContext) -> None:
    await message.answer(
        text=_("Hi admin!"),
        reply_markup=ManageKeyboard.make()
    )
    await state.clear()

@router.message(F.text == "⬅️", StateFilter(None), IsAdmin())
async def manage_back_handler(message: Message, state: FSMContext) -> None:
    await message.answer(
        text=_("Main menu"),
        reply_markup=ManageKeyboard.make()
    )

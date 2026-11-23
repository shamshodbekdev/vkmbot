from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

class BackKeyboard():
    @staticmethod
    def make() -> ReplyKeyboardMarkup:
        builder = ReplyKeyboardBuilder()
        builder.row(
            KeyboardButton(
                text="⬅️",
            )
        )

        return builder.as_markup(resize_keyboard=True)
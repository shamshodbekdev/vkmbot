from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from filters.callback.transcription_language import TranscriptionLanguageCallback
from utils.constants import LOCALES


class TranscriptionLanguageKeyboard:
    @staticmethod
    def make() -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        for code, label in LOCALES:
            builder.button(
                text=label,
                callback_data=TranscriptionLanguageCallback(locale=code).pack(),
            )
        builder.adjust(2)
        return builder.as_markup()

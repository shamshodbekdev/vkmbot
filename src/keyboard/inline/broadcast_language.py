from typing import List
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.i18n import gettext as _
from filters.callback.broadcast_language import BroadcastLanguageCallback
from utils.constants import LANGUAGES


class BroadcastLanguageKeyboard:
    @staticmethod
    def make(selected: List[str]) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        for code, name, choosed in LANGUAGES:
            builder.row(
                InlineKeyboardButton(
                    text=choosed if code in selected else name,
                    callback_data=BroadcastLanguageCallback(
                        language_code=code,
                        action="toggle",
                    ).pack(),
                )
            )
        builder.row(
            InlineKeyboardButton(
                text=_("Continue"),
                icon_custom_emoji_id="5471978009449731768",
                callback_data=BroadcastLanguageCallback(
                    language_code="done",
                    action="done",
                ).pack(),
            )
        )
        builder.adjust(1)
        return builder.as_markup()

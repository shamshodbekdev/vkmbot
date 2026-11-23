from typing import Optional
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.i18n import gettext as _
from filters.callback import LanguageCallback
from utils.constants import LANGUAGES

class LanguageKeyboard():
    @staticmethod
    def make(current: Optional[str] = None, action: Optional[str] = None) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        for code, name, display in LANGUAGES:
            builder.row(
                InlineKeyboardButton(
                    text=display if code == current else name,
                    callback_data=LanguageCallback(
                        language_code=code,
                        action=action
                    ).pack()
                )
            )
        builder.row(
            InlineKeyboardButton(
                text=_("Close"),
                icon_custom_emoji_id="5465665476971471368",
                callback_data=LanguageCallback(
                    language_code=current or "",
                    action="close",
                ).pack(),
            )
        )
        builder.adjust(2)
        return builder.as_markup()
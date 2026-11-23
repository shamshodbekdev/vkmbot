from typing import List, Tuple

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from filters.callback.suggestion import SuggestionCallback


class SuggestionsKeyboard:
    @staticmethod
    def make(suggestions: List[Tuple[str, str]]) -> InlineKeyboardMarkup:
        """``suggestions`` holds ``(text, token)`` pairs; see ``utils.helpers.store_query``."""
        builder = InlineKeyboardBuilder()
        for text, token in suggestions:
            builder.button(
                text=text,
                callback_data=SuggestionCallback(query=token).pack(),
            )
        builder.adjust(1)
        return builder.as_markup()

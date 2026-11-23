from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.i18n import gettext as _

from filters.callback import VideoRecognizeCallback


class VideoRecognizeKeyboard:
    @staticmethod
    def make() -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text=_("Recognize music in video"),
                icon_custom_emoji_id="5188705588925702510",
                callback_data=VideoRecognizeCallback(action="recognize").pack(),
            )
        )
        builder.row(
            InlineKeyboardButton(
                text=_("Close"),
                icon_custom_emoji_id="5465665476971471368",
                callback_data=VideoRecognizeCallback(action="close").pack(),
            )
        )
        return builder.as_markup()

    @staticmethod
    def close_only() -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text=_("Close"),
                icon_custom_emoji_id="5465665476971471368",
                callback_data=VideoRecognizeCallback(action="close").pack(),
            )
        )
        return builder.as_markup()

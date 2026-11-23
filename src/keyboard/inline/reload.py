from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.i18n import gettext as _
from filters.callback.reload import ReloadCallback


class ReloadKeyboard:
    @staticmethod
    def statistics() -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text=_("Reload"),
                icon_custom_emoji_id="5264727218734524899",
                callback_data=ReloadCallback(action="statistics").pack(),
            )
        )
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def analytics() -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text=_("Reload"),
                icon_custom_emoji_id="5264727218734524899",
                callback_data=ReloadCallback(action="analytics").pack(),
            )
        )
        builder.adjust(1)
        return builder.as_markup()

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.i18n import gettext as _
from filters.callback.broadcast_premium import BroadcastPremiumCallback


class BroadcastPremiumKeyboard:
    @staticmethod
    def make() -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text=_("All users"),
                icon_custom_emoji_id="5424885441100782420",
                callback_data=BroadcastPremiumCallback(is_premium=False).pack(),
            )
        )
        builder.row(
            InlineKeyboardButton(
                text=_("Premium only"),
                icon_custom_emoji_id="5435957248314579621",
                callback_data=BroadcastPremiumCallback(is_premium=True).pack(),
            )
        )
        builder.adjust(1)
        return builder.as_markup()

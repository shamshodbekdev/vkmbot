from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.i18n import gettext as _
from filters.callback.broadcast_confirm import BroadcastConfirmCallback


class BroadcastConfirmKeyboard:
    @staticmethod
    def make() -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text=_("Confirm"),
                icon_custom_emoji_id="5427009714745517609",
                callback_data=BroadcastConfirmCallback(
                    action="confirm",
                ).pack(),
            ),
        )
        builder.row(
            InlineKeyboardButton(
                text=_("Cancel"),
                icon_custom_emoji_id="5465665476971471368",
                callback_data=BroadcastConfirmCallback(
                    action="cancel",
                ).pack(),
            ),
        )
        builder.adjust(1)
        return builder.as_markup()

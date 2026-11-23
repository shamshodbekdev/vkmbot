from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.i18n import gettext as _
from filters.callback.broadcast_mode import BroadcastModeCallback
from services.broadcast.enums import BroadcastMode


class BroadcastModeKeyboard:
    @staticmethod
    def make() -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text=_("Copy"),
                icon_custom_emoji_id="5188216731453103384",
                callback_data=BroadcastModeCallback(
                    mode=BroadcastMode.COPY,
                    action="select",
                ).pack(),
            )
        )
        builder.row(
            InlineKeyboardButton(
                text=_("Forward"),
                icon_custom_emoji_id="5229177516727478228",
                callback_data=BroadcastModeCallback(
                    mode=BroadcastMode.FORWARD,
                    action="select",
                ).pack(),
            )
        )
        builder.adjust(1)
        return builder.as_markup()

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.i18n import gettext as _
from aiogram.utils.keyboard import InlineKeyboardBuilder

from filters.callback.broadcast_delay import BroadcastDelayCallback
from utils.constants.broadcast import BROADCAST_DELAYS


class BroadcastDelayKeyboard:
    @staticmethod
    def make() -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        for seconds, label in BROADCAST_DELAYS:
            builder.row(
                InlineKeyboardButton(
                    text=_(label),
                    icon_custom_emoji_id="5451732530048802485",
                    callback_data=BroadcastDelayCallback(
                        seconds=seconds,
                        action="select",
                    ).pack(),
                )
            )
        builder.adjust(1)
        return builder.as_markup()

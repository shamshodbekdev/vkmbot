from typing import List
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.i18n import gettext as _
from filters.callback.broadcast_chat_type import BroadcastChatTypeCallback
from utils.constants.chat_type import CHAT_TYPES


class BroadcastChatTypeKeyboard:
    @staticmethod
    def make(selected: List[str]) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        for code, name, _selected_name in CHAT_TYPES:
            label = _(name)
            builder.row(
                InlineKeyboardButton(
                    text="%s ✅" % label if code in selected else label,
                    callback_data=BroadcastChatTypeCallback(
                        chat_type=code,
                        action="toggle",
                    ).pack(),
                )
            )
        builder.row(
            InlineKeyboardButton(
                text=_("Continue"),
                icon_custom_emoji_id="5471978009449731768",
                callback_data=BroadcastChatTypeCallback(
                    chat_type="done",
                    action="done",
                ).pack(),
            )
        )
        builder.adjust(1)
        return builder.as_markup()

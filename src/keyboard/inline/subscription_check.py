from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.i18n import gettext as _
from database.models import Subscription


class SubscriptionCheckKeyboard:
    @staticmethod
    def make(subscriptions: list[Subscription], check_callback: str) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        for sub in subscriptions:
            if not sub.invite_link:
                continue
            builder.row(
                InlineKeyboardButton(
                    text=_("Subscribe"),
                    icon_custom_emoji_id="5226945370684140473",
                    url=sub.invite_link,
                )
            )
        builder.row(
            InlineKeyboardButton(
                text=_("I have subscribed — check again"),
                icon_custom_emoji_id="5427009714745517609",
                callback_data=check_callback,
            )
        )
        builder.adjust(1)
        return builder.as_markup()

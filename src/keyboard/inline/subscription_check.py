from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.i18n import gettext as _
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.models import Subscription


class SubscriptionCheckKeyboard:
    """One "➕ Subscribe" button per required channel, then "✅ Confirm"."""

    @staticmethod
    def make(subscriptions: list[Subscription], check_callback: str) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        for sub in subscriptions:
            if not sub.invite_link:
                continue
            builder.row(InlineKeyboardButton(text=_("➕ Subscribe"), url=sub.invite_link))
        builder.row(InlineKeyboardButton(text=_("✅ Confirm"), callback_data=check_callback))
        return builder.as_markup()

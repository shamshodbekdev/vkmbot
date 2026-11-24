from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.i18n import gettext as _

from core.bot_identity import add_to_group_url


class StartKeyboard:
    @staticmethod
    def make() -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text=_("Add bot to group"),
                url=add_to_group_url(),
            )
        )
        return builder.as_markup()

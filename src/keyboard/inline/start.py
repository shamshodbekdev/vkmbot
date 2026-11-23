from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.i18n import gettext as _

from core.config import config


class StartKeyboard:
    @staticmethod
    def make() -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text=_("Add bot to group"),
                url="https://t.me/%(username)s?startgroup=true" % dict(username=config.telegram_username.replace("@", "")),
            )
        )
        return builder.as_markup()

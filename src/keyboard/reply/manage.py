from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.utils.i18n import gettext as _

class ManageKeyboard():
    @staticmethod
    def make() -> ReplyKeyboardMarkup:
        builder = ReplyKeyboardBuilder()
        builder.row(
            KeyboardButton(
                text=_("Statistics"),
                icon_custom_emoji_id="5373001317042101552"
            ),
            KeyboardButton(
                text=_("Analytics"),
                icon_custom_emoji_id="5361748661640372834"
            )
        )
        builder.row(
            KeyboardButton(
                text=_("Broadcast message"),
                icon_custom_emoji_id="5334673106202010226"
            )
        )
        builder.row(
            KeyboardButton(
                text=_("Admins"),
                icon_custom_emoji_id="5472308992514464048"
            ),
            KeyboardButton(
                text=_("Users"),
                icon_custom_emoji_id="5427009714745517609"
            )
        )
        builder.row(
            KeyboardButton(
                text=_("Mandatory subscription"),
                icon_custom_emoji_id="5372926953978341366"
            )
        )

        return builder.as_markup(resize_keyboard=True)
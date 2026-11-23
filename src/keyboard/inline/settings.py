from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.i18n import gettext as _
from filters.callback import SettingsCallback
from utils.constants import MAX_RESULTS_CYCLE


class SettingsKeyboard:
    @staticmethod
    def make(language_code: str, max_results: int, like_buttons: bool = True) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text=_("Language"),
                icon_custom_emoji_id="5397575638146110953",
                callback_data=SettingsCallback(action="language", value=0).pack(),
            )
        )
        current_idx = (
            MAX_RESULTS_CYCLE.index(max_results)
            if max_results in MAX_RESULTS_CYCLE
            else MAX_RESULTS_CYCLE.index(10)
        )
        next_val = MAX_RESULTS_CYCLE[(current_idx + 1) % len(MAX_RESULTS_CYCLE)]
        builder.row(
            InlineKeyboardButton(
                text=_("Max results: %(max)s") % dict(max=max_results),
                icon_custom_emoji_id="5226945370684140473",
                callback_data=SettingsCallback(action="max_results", value=next_val).pack(),
            )
        )
        builder.row(
            InlineKeyboardButton(
                text=_("Like buttons: %(status)s") % dict(status="\u2713" if like_buttons else "\u2717"),
                icon_custom_emoji_id="5449505950283078474",
                callback_data=SettingsCallback(action="like_buttons", value=0).pack(),
            )
        )
        builder.row(
            InlineKeyboardButton(
                text=_("Daily charts"),
                icon_custom_emoji_id="5265153614497740567",
                callback_data=SettingsCallback(action="daily_charts", value=0).pack(),
            )
        )
        builder.row(
            InlineKeyboardButton(
                text=_("Close"),
                icon_custom_emoji_id="5465665476971471368",
                callback_data=SettingsCallback(action="close", value=0).pack(),
            )
        )
        return builder.as_markup()

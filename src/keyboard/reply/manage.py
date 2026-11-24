from typing import Optional

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.i18n import gettext as _
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from filters.common.admin import ADMIN, MODERATOR, SUPERADMIN, current_panel_role

_RANK = {MODERATOR: 1, ADMIN: 2, SUPERADMIN: 3}


class ManageKeyboard:
    """Admin panel main menu; shows only the sections the current role may use."""

    @staticmethod
    def make(role: Optional[str] = None) -> ReplyKeyboardMarkup:
        rank = _RANK.get(role or current_panel_role.get(), 2)
        builder = ReplyKeyboardBuilder()
        builder.row(
            KeyboardButton(text=_("Statistics"), icon_custom_emoji_id="5373001317042101552"),
            KeyboardButton(text=_("Analytics"), icon_custom_emoji_id="5361748661640372834"),
        )
        broadcast = KeyboardButton(text=_("Broadcast message"), icon_custom_emoji_id="5334673106202010226")
        users = KeyboardButton(text=_("Users"), icon_custom_emoji_id="5427009714745517609")
        subscription = KeyboardButton(text=_("Mandatory subscription"), icon_custom_emoji_id="5372926953978341366")
        system = KeyboardButton(text=_("🩺 System"))
        if rank >= 3:
            builder.row(broadcast)
            builder.row(KeyboardButton(text=_("Admins"), icon_custom_emoji_id="5472308992514464048"), users)
            builder.row(subscription)
            builder.row(system, KeyboardButton(text=_("📜 Logs")))
        elif rank == 2:
            # Admins have no Admins/Logs buttons, so their rows are paired up instead.
            builder.row(broadcast, users)
            builder.row(subscription, system)
        else:
            builder.row(users)
            builder.row(system)
        builder.row(KeyboardButton(text=_("✖️ Close panel")))
        return builder.as_markup(resize_keyboard=True)

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.i18n import gettext as _
from aiogram.utils.keyboard import InlineKeyboardBuilder

from filters.callback import UserManageCallback
from utils.constants.manage_user import TEMP_BAN_DURATIONS


class ManageUserKeyboard:
    @staticmethod
    def detail(user_id: int, is_blocked: bool, is_temp_banned: bool = False) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text=_("Reload"),
                icon_custom_emoji_id="5264727218734524899",
                callback_data=UserManageCallback(action="reload", user_id=user_id).pack(),
            )
        )
        builder.row(
            InlineKeyboardButton(
                text=_("Unblock user") if is_blocked else _("Block user"),
                icon_custom_emoji_id="5427009714745517609" if is_blocked else "5465665476971471368",
                callback_data=UserManageCallback(action="confirm_toggle_block", user_id=user_id).pack(),
            )
        )
        if not is_blocked:
            builder.row(
                InlineKeyboardButton(
                    text=_("Temp ban"),
                    icon_custom_emoji_id="5265917817546843226",
                    callback_data=UserManageCallback(action="confirm_temp_ban", user_id=user_id).pack(),
                )
            )
        if is_temp_banned:
            builder.row(
                InlineKeyboardButton(
                    text=_("Clear ban"),
                    icon_custom_emoji_id="5427009714745517609",
                    callback_data=UserManageCallback(action="do_clear_ban", user_id=user_id).pack(),
                )
            )
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def confirm_toggle_block(user_id: int, is_blocked: bool) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text=_("Confirm"),
                icon_custom_emoji_id="5427009714745517609",
                callback_data=UserManageCallback(action="do_toggle_block", user_id=user_id).pack(),
            )
        )
        builder.row(
            InlineKeyboardButton(
                text=_("Cancel"),
                icon_custom_emoji_id="5465665476971471368",
                callback_data=UserManageCallback(action="reload", user_id=user_id).pack(),
            )
        )
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def temp_ban_durations(user_id: int, is_temp_banned: bool = False) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        for seconds, label in TEMP_BAN_DURATIONS:
            builder.row(
                InlineKeyboardButton(
                    text=_(label),
                    icon_custom_emoji_id="5265917817546843226",
                    callback_data=UserManageCallback(
                        action="do_temp_ban",
                        user_id=user_id,
                        duration=seconds,
                    ).pack(),
                )
            )
        if is_temp_banned:
            builder.row(
                InlineKeyboardButton(
                    text=_("Clear ban"),
                    icon_custom_emoji_id="5427009714745517609",
                    callback_data=UserManageCallback(action="do_clear_ban", user_id=user_id).pack(),
                )
            )
        builder.row(
            InlineKeyboardButton(
                text=_("Cancel"),
                icon_custom_emoji_id="5465665476971471368",
                callback_data=UserManageCallback(action="reload", user_id=user_id).pack(),
            )
        )
        builder.adjust(1)
        return builder.as_markup()

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.i18n import gettext as _
from filters.callback import AdminCallback
from database.models import User
from database.enums import UserRole

class ManageAdminKeyboard:
    @staticmethod
    async def list() -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        for user in await User.filter(role=UserRole.ADMINISTRATOR):
            builder.row(
                InlineKeyboardButton(
                    text=user.display_name,
                    icon_custom_emoji_id="5424885441100782420",
                    callback_data=AdminCallback(action="select", admin_id=user.telegram_id).pack()
                )
            )
        builder.row(
            InlineKeyboardButton(
                text=_("Add admin"),
                icon_custom_emoji_id="5226945370684140473",
                callback_data=AdminCallback(action="add").pack()
            )
        )
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def detail(admin_id: int) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text=_("Delete admin"),
                icon_custom_emoji_id="5465665476971471368",
                callback_data=AdminCallback(action="confirm_delete", admin_id=admin_id).pack()
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="⬅️",
                callback_data=AdminCallback(action="list").pack()
            )
        )
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def confirm_add(admin_id: int) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text=_("Confirm"),
                icon_custom_emoji_id="5427009714745517609",
                callback_data=AdminCallback(action="do_add", admin_id=admin_id).pack()
            )
        )
        builder.row(
            InlineKeyboardButton(
                text=_("Cancel"),
                icon_custom_emoji_id="5465665476971471368",
                callback_data=AdminCallback(action="list").pack()
            )
        )
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def confirm_delete(admin_id: int) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text=_("Confirm"),
                icon_custom_emoji_id="5427009714745517609",
                callback_data=AdminCallback(action="do_delete", admin_id=admin_id).pack()
            )
        )
        builder.row(
            InlineKeyboardButton(
                text=_("Cancel"),
                icon_custom_emoji_id="5465665476971471368",
                callback_data=AdminCallback(action="select", admin_id=admin_id).pack()
            )
        )
        builder.adjust(1)
        return builder.as_markup()

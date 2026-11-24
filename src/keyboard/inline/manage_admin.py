from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.i18n import gettext as _
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.enums import STAFF_ROLES, UserRole
from database.models import User
from filters.callback import AdminCallback

ROLE_ICONS = {UserRole.ADMINISTRATOR: "👮", UserRole.MODERATOR: "🛡"}


class ManageAdminKeyboard:
    @staticmethod
    async def list() -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        for user in await User.filter(role__in=STAFF_ROLES).order_by("role", "created_at"):
            builder.row(
                InlineKeyboardButton(
                    text="%s %s" % (ROLE_ICONS.get(user.role, ""), user.display_name),
                    callback_data=AdminCallback(action="select", admin_id=user.telegram_id).pack(),
                )
            )
        builder.row(InlineKeyboardButton(text=_("➕ Add admin"), callback_data=AdminCallback(action="add").pack()))
        return builder.as_markup()

    @staticmethod
    def detail(admin_id: int, role: UserRole = UserRole.ADMINISTRATOR) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        if role == UserRole.ADMINISTRATOR:
            builder.row(InlineKeyboardButton(
                text=_("🛡 Make moderator"),
                callback_data=AdminCallback(action="set_role", admin_id=admin_id, role=UserRole.MODERATOR.value).pack(),
            ))
        else:
            builder.row(InlineKeyboardButton(
                text=_("👮 Make admin"),
                callback_data=AdminCallback(action="set_role", admin_id=admin_id, role=UserRole.ADMINISTRATOR.value).pack(),
            ))
        builder.row(InlineKeyboardButton(
            text=_("🗑 Remove from team"),
            callback_data=AdminCallback(action="confirm_delete", admin_id=admin_id).pack(),
        ))
        builder.row(InlineKeyboardButton(text="⬅️", callback_data=AdminCallback(action="list").pack()))
        return builder.as_markup()

    @staticmethod
    def confirm_add(admin_id: int) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text=_("👮 Admin"),
                callback_data=AdminCallback(action="do_add", admin_id=admin_id, role=UserRole.ADMINISTRATOR.value).pack(),
            ),
            InlineKeyboardButton(
                text=_("🛡 Moderator"),
                callback_data=AdminCallback(action="do_add", admin_id=admin_id, role=UserRole.MODERATOR.value).pack(),
            ),
        )
        builder.row(InlineKeyboardButton(text=_("Cancel"), callback_data=AdminCallback(action="list").pack()))
        return builder.as_markup()

    @staticmethod
    def confirm_delete(admin_id: int) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text=_("Confirm"), callback_data=AdminCallback(action="do_delete", admin_id=admin_id).pack()))
        builder.row(InlineKeyboardButton(text=_("Cancel"), callback_data=AdminCallback(action="select", admin_id=admin_id).pack()))
        return builder.as_markup()

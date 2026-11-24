from html import escape
import datetime
from aiogram.utils.i18n import gettext as _
from database.enums import UserRole
from database.models import User

UTC = datetime.timezone.utc


def build_admins_list(total: int) -> str:
    return _(
        "<b>👥 Team</b>  —  <b>%(total)s</b>\n"
        "\n"
        "👮 <b>Admin</b> — users, statistics, broadcasts, mandatory subscriptions.\n"
        "🛡 <b>Moderator</b> — users, statistics and system status only.\n"
        "\n"
        "Select a person to change their role or remove them,\n"
        "or tap <b>➕ Add admin</b> to add someone."
    ) % dict(total=total)


def build_admin_detail(user: User) -> str:
    now = datetime.datetime.now(UTC)
    return _(
        "<b>%(name)s</b>\n"
        "\n"
        "Role         —  <b>%(role)s</b>\n"
        "Telegram ID  —  <b>%(telegram_id)s</b>\n"
        "Language     —  <b>%(language)s</b>\n"
        "Premium      —  <b>%(premium)s</b>\n"
        "Blocked      —  <b>%(blocked)s</b>\n"
        "Chat type    —  <b>%(chat_type)s</b>\n"
        "Joined       —  <b>%(joined)s</b>\n"
        "\n"
        "Refreshed at: <i>%(refreshed_at)s</i>"
    ) % dict(
        name=escape(user.display_name),
        role=_("👮 Admin") if user.role == UserRole.ADMINISTRATOR else _("🛡 Moderator"),
        telegram_id=user.telegram_id,
        language=user.language_code.upper(),
        premium=_("Yes") if user.is_premium else _("No"),
        blocked=_("Yes") if user.is_blocked else _("No"),
        chat_type=user.chat_type.value.capitalize(),
        joined=user.created_at.strftime("%d.%m.%Y"),
        refreshed_at=now.strftime("%d.%m.%Y %H:%M:%S"),
    )

from html import escape
import datetime
from aiogram.utils.i18n import gettext as _
from database.models import User

UTC = datetime.timezone.utc


def build_admins_list(total: int) -> str:
    return _(
        "<b>Admins</b>  —  <b>%(total)s</b>\n"
        "\n"
        "Admins have full access to the management panel.\n"
        "They can manage users, subscriptions, and broadcasts.\n"
        "\n"
        "Select an admin from the list below to view details\n"
        "or tap <b>Add admin</b> to grant access to a new user."
    ) % dict(total=total)


def build_admin_detail(user: User) -> str:
    now = datetime.datetime.now(UTC)
    return _(
        "<b>%(name)s</b>\n"
        "\n"
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
        telegram_id=user.telegram_id,
        language=user.language_code.upper(),
        premium=_("Yes") if user.is_premium else _("No"),
        blocked=_("Yes") if user.is_blocked else _("No"),
        chat_type=user.chat_type.value.capitalize(),
        joined=user.created_at.strftime("%d.%m.%Y"),
        refreshed_at=now.strftime("%d.%m.%Y %H:%M:%S"),
    )

from html import escape
import datetime
from aiogram.utils.i18n import gettext as _
from database.models import User
from utils.helpers.manage_user import is_temp_banned

UTC = datetime.timezone.utc


def build_users_list(total: int, blocked: int) -> str:
    return _(
        "<b>Users</b>  —  <b>%(total)s</b>\n"
        "\n"
        "Blocked  —  <b>%(blocked)s</b>\n"
        "\n"
        "Send a <b>Telegram ID</b> or a <b>name</b> to find a user."
    ) % dict(total=total, blocked=blocked)


def build_user_detail(user: User) -> str:
    now = datetime.datetime.now(UTC)
    temp_banned = is_temp_banned(user)
    banned_until_line = (
        "\n%(label)s  —  <b>%(t)s</b>" % dict(
            label=_("Banned until"),
            t=user.blocked_until.strftime("%d.%m.%Y %H:%M UTC"),
        )
        if temp_banned
        else ""
    )
    return _(
        "<b>%(name)s</b>\n"
        "\n"
        "Telegram ID  —  <b>%(telegram_id)s</b>\n"
        "Language     —  <b>%(language)s</b>\n"
        "Premium      —  <b>%(premium)s</b>\n"
        "Blocked      —  <b>%(blocked)s</b>%(banned_until_line)s\n"
        "Chat type    —  <b>%(chat_type)s</b>\n"
        "Status       —  <b>%(status)s</b>\n"
        "Joined       —  <b>%(joined)s</b>\n"
        "Last active  —  <b>%(last_active)s</b>\n"
        "\n"
        "Refreshed at: <i>%(refreshed_at)s</i>"
    ) % dict(
        name=escape(user.display_name),
        telegram_id=user.telegram_id,
        language=user.language_code.upper(),
        premium=_("Yes") if user.is_premium else _("No"),
        blocked=_("Yes") if user.is_blocked else _("No"),
        banned_until_line=banned_until_line,
        chat_type=user.chat_type.value.capitalize(),
        status=user.chat_status.value.capitalize(),
        joined=user.created_at.strftime("%d.%m.%Y"),
        last_active=user.updated_at.strftime("%d.%m.%Y %H:%M UTC") if user.updated_at else "—",
        refreshed_at=now.strftime("%d.%m.%Y %H:%M:%S"),
    )

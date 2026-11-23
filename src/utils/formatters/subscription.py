from html import escape
import datetime
from aiogram.utils.i18n import gettext as _
from database.models import Subscription

UTC = datetime.timezone.utc


def build_subscriptions_list(total: int, active: int) -> str:
    return _(
        "<b>Mandatory subscription</b>  —  <b>%(total)s</b>\n"
        "\n"
        "Active  —  <b>%(active)s</b>\n"
        "\n"
        "Select a subscription below or add a new one."
    ) % dict(total=total, active=active)


def build_sub_detail(sub: Subscription) -> str:
    status = _("Active") if sub.is_active else _("Inactive")
    max_audience = str(sub.maximum_audience) if sub.maximum_audience else "—"
    tracker = "%(joined)s / %(max)s" % dict(joined=sub.joined_count, max=max_audience)
    updated_at = sub.updated_at.strftime("%d.%m.%Y %H:%M:%S")
    refreshed_at = datetime.datetime.now(UTC).strftime("%d.%m.%Y %H:%M:%S")
    return _(
        "<b>%(title)s</b>\n"
        "\n"
        "Type      —  <b>%(chat_type)s</b>\n"
        "Chat ID   —  <b>%(chat_id)s</b>\n"
        "Status    —  <b>%(status)s</b>\n"
        "Tracker   —  <b>%(tracker)s</b>\n"
        "\n"
        "Updated at:   <i>%(updated_at)s</i>\n"
        "Refreshed at: <i>%(refreshed_at)s</i>"
    ) % dict(
        title=escape(sub.title),
        chat_type=sub.chat_type.value.capitalize(),
        chat_id=sub.chat_id,
        status=status,
        tracker=tracker,
        updated_at=updated_at,
        refreshed_at=refreshed_at,
    )

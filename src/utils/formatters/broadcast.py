import datetime
import humanize
from aiogram.utils.i18n import gettext as _
from database.models.broadcast import BroadcastRecord

UTC = datetime.timezone.utc


def build_broadcast_list(total: int) -> str:
    return _(
        "<b>Broadcast</b>  —  <b>%(total)s</b>\n"
        "\n"
        "Select a broadcast to view details or start a new one."
    ) % dict(total=total)


def build_record_detail(record: BroadcastRecord) -> str:
    langs = ", ".join(record.languages) if record.languages else "—"
    chat_types = ", ".join(t.capitalize() for t in record.chat_types) if record.chat_types else "—"
    premium = _("Yes") if record.is_premium else _("No")
    percent = round(record.success / record.audience * 100) if record.audience else 0
    return _(
        "<b>Broadcast</b>\n"
        "\n"
        "Languages   —  <b>%(langs)s</b>\n"
        "Chat types  —  <b>%(chat_types)s</b>\n"
        "Premium     —  <b>%(premium)s</b>\n"
        "Mode        —  <b>%(mode)s</b>\n"
        "\n"
        "Audience    —  <b>%(audience)s</b>\n"
        "Success     —  <b>%(success)s  (%(percent)s%%)</b>\n"
        "Failed      —  <b>%(failed)s</b>\n"
        "Blocked     —  <b>%(blocked)s</b>\n"
        "\n"
        "Created at: <i>%(created_at)s</i>"
    ) % dict(
        langs=langs,
        chat_types=chat_types,
        premium=premium,
        mode=record.mode.capitalize(),
        audience=record.audience,
        success=record.success,
        percent=percent,
        failed=record.failed,
        blocked=record.blocked,
        created_at=record.created_at.strftime("%d.%m.%Y %H:%M:%S"),
    )


def build_broadcast_summary(audience: int, mode: str, delay_label: str) -> str:
    return _(
        "<b>Broadcast</b>\n"
        "\n"
        "Audience  —  <b>%(audience)s users</b>\n"
        "Mode      —  <b>%(mode)s</b>\n"
        "Delay     —  <b>%(delay)s</b>\n"
        "\n"
        "Confirm to start broadcasting."
    ) % dict(
        audience=humanize.intcomma(audience),
        delay=delay_label,
        mode=mode,
    )


def build_broadcast_started(audience: int, mode: str, delay_label: str) -> str:
    return _(
        "<b>Broadcast is running</b>\n"
        "\n"
        "Audience  —  <b>%(audience)s users</b>\n"
        "Mode      —  <b>%(mode)s</b>\n"
        "Delay     —  <b>%(delay)s</b>\n"
        "Datetime  —  <b>%(datetime)s</b>"
    ) % dict(
        audience=humanize.intcomma(audience),
        delay=delay_label,
        mode=mode,
        datetime=datetime.datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
    )


def build_broadcast_progress(progress: dict, status: str) -> str:
    return _(
        "Status:    %(status)s  —  %(percent)s%%\n"
        "\n"
        "Sent:      %(total)s / %(audience)s\n"
        "Success:   %(success)s\n"
        "Failed:    %(failed)s\n"
        "Blocked:   %(blocked)s\n"
        "\n"
        "Started:   %(started_at)s"
    ) % dict(
        status=status,
        percent=progress["percent"],
        total=humanize.intcomma(progress["total"]),
        audience=humanize.intcomma(progress["audience"]),
        success=humanize.intcomma(progress["success"]),
        failed=humanize.intcomma(progress["failed"]),
        blocked=humanize.intcomma(progress["blocked"]),
        started_at=progress["started_at"],
    )

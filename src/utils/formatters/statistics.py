import datetime
import humanize
from aiogram.utils.i18n import gettext as _

UTC = datetime.timezone.utc


def build_statistics_caption(report) -> str:
    groups = (
        report.summary.types.group.count
        + report.summary.types.supergroup.count
        + report.summary.types.channel.count
    )
    active_groups = (
        report.summary.status.administrator.count
        + report.summary.status.creator.count
    )
    return _(
        "<b>Bot statistics</b>\n"
        "\n"
        "Total audience: <b>%(total_word)s</b>\n"
        "\n"
        "<b>Users: %(private)s (+%(daily_new)s) (-%(kicked)s)</b>\n"
        "%(uz)s UZ  |  %(en)s EN  |  %(ru)s RU\n"
        "Premium: %(premium)s\n"
        "Active: %(member)s\n"
        "Kicked: %(kicked)s\n"
        "\n"
        "<b>Groups: %(groups)s (+%(daily_active)s) (-%(left)s)</b>\n"
        "Active: %(active_groups)s\n"
        "Left: %(left)s\n"
        "\n"
        "Updated at: <i>%(updated_at)s</i>"
    ) % dict(
        total_word=humanize.intword(report.summary.total_count.total),
        private=humanize.intcomma(report.summary.types.private.count),
        daily_new=humanize.intcomma(report.daily.new_private.count),
        kicked=humanize.intcomma(report.summary.status.kicked.count),
        uz=humanize.intcomma(report.summary.languages.uz.count),
        en=humanize.intcomma(report.summary.languages.en.count),
        ru=humanize.intcomma(report.summary.languages.ru.count),
        premium=humanize.intcomma(report.summary.premium.count),
        member=humanize.intcomma(report.summary.status.member.count),
        groups=humanize.intcomma(groups),
        daily_active=humanize.intcomma(report.daily.new_groups.count),
        left=humanize.intcomma(report.summary.status.left.count),
        active_groups=humanize.intcomma(active_groups),
        updated_at=datetime.datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
    )

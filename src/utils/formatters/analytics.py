import datetime
import humanize
from aiogram.utils.i18n import gettext as _
from schemas.health import HealthSchema

UTC = datetime.timezone.utc


def build_analytics_caption(report, health: HealthSchema) -> str:
    du = report.daily.users
    wu = report.weekly.users
    mu = report.monthly.users
    dl = report.daily.languages
    wl = report.weekly.languages
    ml = report.monthly.languages
    return _(
        "<b>Analytics</b>\n"
        "\n"
        "<b>Daily: %(d_current)s  (%(d_change)s,  %(d_rate)s%%)</b>\n"
        "UZ %(d_uz)s  |  EN %(d_en)s  |  RU %(d_ru)s\n"
        "\n"
        "<b>Weekly: %(w_current)s  (%(w_change)s,  %(w_rate)s%%)</b>\n"
        "UZ %(w_uz)s  |  EN %(w_en)s  |  RU %(w_ru)s\n"
        "\n"
        "<b>Monthly: %(m_current)s  (%(m_change)s,  %(m_rate)s%%)</b>\n"
        "UZ %(m_uz)s  |  EN %(m_en)s  |  RU %(m_ru)s\n"
        "\n"
        "<b>Health</b>\n"
        "Database: %(database)s  |  Scheduler: %(queue)s  |  Cache: %(cache)s  |  Bot: %(bot)s\n"
        "\n"
        "Updated at: <i>%(updated_at)s</i>"
    ) % dict(
        d_current=humanize.intcomma(du.current),
        d_change=humanize.intcomma(du.change),
        d_rate=round(du.rate, 1),
        d_uz=humanize.intcomma(dl.uz.current),
        d_en=humanize.intcomma(dl.en.current),
        d_ru=humanize.intcomma(dl.ru.current),
        w_current=humanize.intcomma(wu.current),
        w_change=humanize.intcomma(wu.change),
        w_rate=round(wu.rate, 1),
        w_uz=humanize.intcomma(wl.uz.current),
        w_en=humanize.intcomma(wl.en.current),
        w_ru=humanize.intcomma(wl.ru.current),
        m_current=humanize.intcomma(mu.current),
        m_change=humanize.intcomma(mu.change),
        m_rate=round(mu.rate, 1),
        m_uz=humanize.intcomma(ml.uz.current),
        m_en=humanize.intcomma(ml.en.current),
        m_ru=humanize.intcomma(ml.ru.current),
        database=_("Yes") if health.database else _("No"),
        queue=_("Yes") if health.queue else _("No"),
        cache=_("Yes") if health.cache else _("No"),
        bot=_("Yes") if health.bot else _("No"),
        updated_at=datetime.datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
    )

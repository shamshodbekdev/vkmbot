import io

from aiogram.utils.i18n import gettext as _
from matplotlib.ticker import FuncFormatter, MaxNLocator

from schemas.analytics import AnalyticsReportSchema, GrowthSchema
from services.charts import style


def _delta(growth: GrowthSchema):
    """Change vs the previous period as text + colour; the arrow carries the meaning, not the colour alone."""
    if growth.change > 0:
        return "▲ +%s  (+%g%%)" % (style.number(growth.change), round(growth.rate, 1)), style.UP
    if growth.change < 0:
        return "▼ −%s  (−%g%%)" % (style.number(-growth.change), abs(round(growth.rate, 1))), style.DOWN
    return "— " + _("no change"), style.MUTED


class AnalyticsChartService:
    """Admin "Analytics" picture: 30-day new-user trend + today / 7 / 30 day comparison + languages."""

    @classmethod
    def _trend(cls, fig, report: AnalyticsReportSchema) -> None:
        ax = fig.add_axes((0.1, 0.48, 0.86, 0.33))
        days = [point.day for point in report.daily_new]
        counts = [point.count for point in report.daily_new]
        x = list(range(len(days)))

        if x:
            ax.fill_between(x, counts, color=style.SERIES, alpha=0.12, linewidth=0, zorder=1)
            ax.plot(x, counts, color=style.SERIES, linewidth=2, solid_joinstyle="round", zorder=2)
            # Mark and label only the last day and the best day.
            peak = max(range(len(counts)), key=lambda i: (counts[i], i))
            for index in sorted({peak, len(x) - 1}):
                ax.scatter([index], [counts[index]], s=42, color=style.SERIES,
                           edgecolors=style.SURFACE, linewidths=2, zorder=3)
                ax.annotate(style.number(counts[index]), (index, counts[index]), xytext=(0, 9),
                            textcoords="offset points", ha="center", fontsize=9.5,
                            fontweight="bold", color=style.INK, family=style.FONT)
            step = max(1, len(x) // 6)
            ticks = list(range(len(x) - 1, -1, -step))[::-1]
            ax.set_xticks(ticks)
            ax.set_xticklabels([days[i].strftime("%d.%m") for i in ticks])
            ax.set_xlim(-0.5, len(x) - 0.5)
            ax.set_ylim(0, max(max(counts), 1) * 1.25)
        ax.yaxis.set_major_locator(MaxNLocator(nbins=4, integer=True))
        ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _pos: style.compact(value)))
        ax.grid(axis="y", color=style.GRID, linewidth=0.8, zorder=0)
        ax.set_axisbelow(True)
        style.clean_axes(ax)
        ax.set_xlabel(_("Days"), fontsize=9.5, color=style.MUTED, family=style.FONT, labelpad=6)
        ax.set_ylabel(_("New users"), fontsize=9.5, color=style.MUTED, family=style.FONT, labelpad=8)

    @classmethod
    def generate(cls, report: AnalyticsReportSchema) -> io.BytesIO:
        fig = style.new_figure(10, 7.2)
        style.header(fig, _("Analytics"), _("New users · last 30 days"))
        cls._trend(fig, report)

        periods = (
            (_("Last 24 hours"), report.daily.users),
            (_("Last 7 days"), report.weekly.users),
            (_("Last 30 days"), report.monthly.users),
        )
        left, gap, width = 0.04, 0.018, 0.175
        for index, (label, growth) in enumerate(periods):
            note, color = _delta(growth)
            style.tile(fig, (left + index * (width + gap), 0.08, width, 0.25),
                       label, style.number(growth.current), note, color)
        fig.text(0.04, 0.36, _("Compared with the previous period"), fontsize=10,
                 color=style.INK_SECONDARY, family=style.FONT)

        languages = report.monthly.languages
        style.hbars(fig, (0.62, 0.08, 0.34, 0.27), _("By language · 30 days"), [
            ("O'zbek", languages.uz.current),
            ("Русский", languages.ru.current),
            ("English", languages.en.current),
            (_("Not chosen"), languages.not_set.current),
        ], label_width=0.1)

        style.footer(fig)
        return style.to_png(fig)

import io

from aiogram.utils.i18n import gettext as _

from schemas.statistics import StatisticsReportSchema
from services.charts import style


class StatisticsChartService:
    """Admin "Statistics" picture: 4 headline tiles + languages / chat types / media bars."""

    @staticmethod
    def generate(report: StatisticsReportSchema) -> io.BytesIO:
        summary = report.summary
        media = report.media
        media_total = media.youtube.total + media.instagram.total + media.tiktok.total

        fig = style.new_figure(10, 6.6)
        style.header(fig, _("Statistics"), _("Bot audience at a glance"))

        tiles = (
            (_("Total users"), summary.total_count.total),
            (_("Active · 30 days"), report.monthly.active_private.count),
            (_("New today"), report.daily.new_private.count),
            (_("Saved media"), media_total),
        )
        left, gap, width = 0.04, 0.02, (0.92 - 3 * 0.02) / 4
        for index, (label, value) in enumerate(tiles):
            style.tile(fig, (left + index * (width + gap), 0.62, width, 0.19), label, style.number(value))

        languages = summary.languages
        types = summary.types
        panels = (
            (_("Languages"), [
                ("O'zbek", languages.uz.count),
                ("Русский", languages.ru.count),
                ("English", languages.en.count),
                (_("Not chosen"), languages.not_set.count),
            ]),
            (_("Chat types"), [
                (_("Private chats"), types.private.count),
                (_("Groups"), types.group.count),
                (_("Supergroups"), types.supergroup.count),
                (_("Channels"), types.channel.count),
            ]),
            (_("Media by platform"), [
                ("YouTube", media.youtube.total),
                ("Instagram", media.instagram.total),
                ("TikTok", media.tiktok.total),
            ]),
        )
        column = 0.92 / 3
        for index, (title, items) in enumerate(panels):
            style.hbars(fig, (0.04 + index * column, 0.1, column - 0.02, 0.42), title, items)

        style.footer(fig)
        return style.to_png(fig)

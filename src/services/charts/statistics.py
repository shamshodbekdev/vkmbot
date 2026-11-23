import io
import numpy as np
from schemas.statistics import StatisticsReportSchema

import matplotlib

matplotlib.use("Agg")

from matplotlib.axes import Axes  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402


class StatisticsChartService:
    @staticmethod
    def _plot(ax: Axes, labels: list, values: list) -> None:
        x = list(range(len(labels)))
        x_smooth = np.linspace(0, len(x) - 1, 200)
        coeffs = np.polyfit(x, values, min(2, len(x) - 1))
        y_smooth = np.polyval(coeffs, x_smooth)
        ax.plot(x_smooth, y_smooth, "-", color="#1a6bbf", linewidth=1.8, zorder=2)
        ax.scatter(x, values, marker="x", color="#1a4a8a", s=70, linewidths=2, zorder=3)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=9)

    @staticmethod
    def _style(ax: Axes, title: str) -> None:
        ax.set_title(title, fontsize=10, pad=8)
        ax.grid(True, linestyle="-", linewidth=0.5, color="#dddddd")
        ax.set_axisbelow(True)
        for spine in ax.spines.values():
            spine.set_linewidth(0.8)
            spine.set_color("#aaaaaa")
        ax.tick_params(colors="#444444", length=0)
        ax.yaxis.set_tick_params(labelsize=8)

    @classmethod
    def _ax_languages(cls, ax: Axes, report: StatisticsReportSchema) -> None:
        languages = report.summary.languages
        labels = ["uz", "ru", "en", "not set"]
        values = [
            languages.uz.count,
            languages.ru.count,
            languages.en.count,
            languages.not_set.count,
        ]
        cls._plot(ax, labels, values)
        cls._style(ax, "Languages")

    @classmethod
    def _ax_types(cls, ax: Axes, report: StatisticsReportSchema) -> None:
        types = report.summary.types
        labels = ["private", "group", "supergroup", "channel"]
        values = [
            types.private.count,
            types.group.count,
            types.supergroup.count,
            types.channel.count,
        ]
        cls._plot(ax, labels, values)
        cls._style(ax, "Chat types")

    @classmethod
    def _ax_activity(cls, ax: Axes, report: StatisticsReportSchema) -> None:
        labels = ["d.priv", "d.grp", "w.priv", "w.grp", "m.priv", "m.grp"]
        values = [
            report.daily.new_private.count,
            report.daily.new_groups.count,
            report.weekly.new_private.count,
            report.weekly.new_groups.count,
            report.monthly.new_private.count,
            report.monthly.new_groups.count,
        ]
        cls._plot(ax, labels, values)
        cls._style(ax, "Activity")

    @classmethod
    def _ax_media(cls, ax: Axes, report: StatisticsReportSchema) -> None:
        labels = ["YouTube", "Instagram", "TikTok"]
        values = [
            report.media.youtube.total,
            report.media.instagram.total,
            report.media.tiktok.total,
        ]
        cls._plot(ax, labels, values)
        cls._style(ax, "Cached media")

    @classmethod
    def generate(cls, report: StatisticsReportSchema) -> io.BytesIO:
        fig = Figure(figsize=(14, 10))
        axes = fig.subplots(2, 2)
        fig.patch.set_facecolor("#ffffff")
        fig.subplots_adjust(hspace=0.5, wspace=0.35, left=0.08, right=0.97, top=0.93, bottom=0.06)

        cls._ax_languages(axes[0][0], report)
        cls._ax_types(axes[0][1], report)
        cls._ax_activity(axes[1][0], report)
        cls._ax_media(axes[1][1], report)

        buffer = io.BytesIO()
        fig.savefig(buffer, format="png", dpi=160, bbox_inches="tight")
        buffer.seek(0)
        return buffer
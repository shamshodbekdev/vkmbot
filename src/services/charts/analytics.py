import io
import numpy as np
from schemas.analytics import AnalyticsReportSchema

import matplotlib

matplotlib.use("Agg")

from matplotlib.axes import Axes  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402


class AnalyticsChartService:
    @staticmethod
    def _plot_two(ax: Axes, labels: list, current: list, previous: list) -> None:
        x = list(range(len(labels)))
        x_smooth = np.linspace(0, len(x) - 1, 200)
        coeffs = np.polyfit(x, current, min(2, len(x) - 1))
        y_smooth = np.polyval(coeffs, x_smooth)
        ax.plot(x_smooth, y_smooth, "-", color="#1a6bbf", linewidth=1.8, zorder=2)
        ax.scatter(x, current, marker="x", color="#1a4a8a", s=70, linewidths=2, zorder=3)
        ax.plot(x, previous, "o--", color="#7ab0e0", linewidth=1.2, markersize=5, zorder=1)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=9)
        ax.axhline(0, color="#cccccc", linewidth=0.6, linestyle=":")

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
    def _ax_growth(cls, ax: Axes, report: AnalyticsReportSchema) -> None:
        labels = ["daily", "weekly", "monthly"]
        current = [
            report.daily.users.current,
            report.weekly.users.current,
            report.monthly.users.current,
        ]
        previous = [
            report.daily.users.previous,
            report.weekly.users.previous,
            report.monthly.users.previous,
        ]
        cls._plot_two(ax, labels, current, previous)
        cls._style(ax, "New users  (current vs previous)")

    @classmethod
    def _ax_rates(cls, ax: Axes, report: AnalyticsReportSchema) -> None:
        labels = ["daily", "weekly", "monthly"]
        rates = [
            report.daily.users.rate,
            report.weekly.users.rate,
            report.monthly.users.rate,
        ]
        x = list(range(len(labels)))
        x_smooth = np.linspace(0, len(x) - 1, 200)
        coeffs = np.polyfit(x, rates, min(2, len(x) - 1))
        y_smooth = np.polyval(coeffs, x_smooth)
        ax.plot(x_smooth, y_smooth, "-", color="#1a6bbf", linewidth=1.8, zorder=2)
        ax.scatter(x, rates, marker="x", color="#1a4a8a", s=70, linewidths=2, zorder=3)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=9)
        ax.axhline(0, color="#aaaaaa", linewidth=0.8, linestyle="--")
        cls._style(ax, "Growth rate %")

    @classmethod
    def _ax_language_rates(cls, ax: Axes, report: AnalyticsReportSchema) -> None:
        labels = ["uz", "ru", "en", "not set"]
        langs = report.daily.languages
        current = [langs.uz.current, langs.ru.current, langs.en.current, langs.not_set.current]
        previous = [langs.uz.previous, langs.ru.previous, langs.en.previous, langs.not_set.previous]
        cls._plot_two(ax, labels, current, previous)
        cls._style(ax, "Language growth  (current vs previous)")

    @classmethod
    def generate(cls, report: AnalyticsReportSchema) -> io.BytesIO:
        fig = Figure(figsize=(10, 12))
        axes = fig.subplots(3, 1)
        fig.patch.set_facecolor("#ffffff")
        fig.subplots_adjust(hspace=0.5, left=0.12, right=0.97, top=0.93, bottom=0.06)

        cls._ax_growth(axes[0], report)
        cls._ax_rates(axes[1], report)
        cls._ax_language_rates(axes[2], report)

        buffer = io.BytesIO()
        fig.savefig(buffer, format="png", dpi=160, bbox_inches="tight")
        buffer.seek(0)
        return buffer
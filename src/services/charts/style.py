"""Shared look for the admin panel charts (Statistics / Analytics).

One light theme, tuned for a phone screen: a single blue for data, ink-coloured
text, hairline grid. All visible text goes through gettext, so the chart is drawn
in the admin's language (the caller's i18n context is copied into the worker
thread by ``asyncio.to_thread``).
"""
import datetime
import io
from typing import List, Sequence, Tuple
from zoneinfo import ZoneInfo

import matplotlib

matplotlib.use("Agg")

from aiogram.utils.i18n import gettext as _  # noqa: E402
from matplotlib.axes import Axes  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

# Colour tokens (validated: blue passes contrast >= 3:1 on the surface).
SURFACE = "#fcfcfb"
TILE = "#f3f2ee"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
SERIES = "#2a78d6"
UP = "#006300"
DOWN = "#d03b3b"

FONT = "DejaVu Sans"  # covers Latin + Cyrillic (uz, uzc, ru, en)
DPI = 150
TIMEZONE = "Asia/Tashkent"


def number(value: float) -> str:
    """1234567 -> '1 234 567' (thin, language-neutral grouping)."""
    return "{:,}".format(int(round(value))).replace(",", " ")


def compact(value: float) -> str:
    """Short axis/label form: 950, 12.4K, 1.2M."""
    value = float(value)
    for limit, suffix in ((1_000_000, "M"), (1_000, "K")):
        if abs(value) >= limit:
            text = ("%.1f" % (value / limit)).rstrip("0").rstrip(".")
            return text + suffix
    return number(value)


def new_figure(width: float, height: float) -> Figure:
    fig = Figure(figsize=(width, height), dpi=DPI)
    fig.patch.set_facecolor(SURFACE)
    return fig


def header(fig: Figure, title: str, subtitle: str) -> None:
    fig.text(0.04, 0.955, title, fontsize=22, fontweight="bold", color=INK, family=FONT, va="top")
    fig.text(0.04, 0.885, subtitle, fontsize=11, color=INK_SECONDARY, family=FONT, va="top")


def footer(fig: Figure) -> None:
    now = datetime.datetime.now(ZoneInfo(TIMEZONE)).strftime("%d.%m.%Y %H:%M")
    fig.text(
        0.04, 0.025, _("Updated: %(time)s (Tashkent time)") % dict(time=now),
        fontsize=9, color=MUTED, family=FONT, va="bottom",
    )


def tile(fig: Figure, box: Tuple[float, float, float, float], label: str, value: str,
         note: str = "", note_color: str = MUTED) -> None:
    """A stat tile: muted label on top, big number, optional small note underneath."""
    x, y, w, h = box
    fig.patches.append(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0,rounding_size=0.012",
        transform=fig.transFigure, facecolor=TILE, edgecolor="none", zorder=0,
    ))
    pad = 0.018
    fig.text(x + pad, y + h - 0.03, label, fontsize=10, color=INK_SECONDARY, family=FONT, va="top")
    fig.text(x + pad, y + h * 0.42, value, fontsize=21, fontweight="bold", color=INK, family=FONT, va="center")
    if note:
        fig.text(x + pad, y + 0.022, note, fontsize=9.5, color=note_color, family=FONT, va="bottom",
                 fontweight="bold" if note_color != MUTED else "normal")


def clean_axes(ax: Axes) -> None:
    ax.set_facecolor(SURFACE)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(BASELINE)
    ax.tick_params(colors=INK_SECONDARY, length=0, labelsize=9)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_family(FONT)


def hbars(fig: Figure, column: Tuple[float, float, float, float], title: str,
          items: Sequence[Tuple[str, int]], show_share: bool = True, label_width: float = 0.1) -> Axes:
    """Ranked horizontal bars in one colour inside ``column`` (figure coords), title on top,
    category names on the left, value (+ share) written at each bar's end."""
    x, y0, width, height = column
    rows: List[Tuple[str, int]] = sorted(items, key=lambda item: item[1], reverse=True)
    values = [value for _label, value in rows]
    total = sum(values) or 1
    peak = max(values) or 1
    y = list(range(len(rows)))[::-1]

    fig.text(x, y0 + height, title, fontsize=11.5, fontweight="bold", color=INK, family=FONT, va="bottom")
    ax = fig.add_axes((x + label_width, y0, width - label_width, height - 0.045))
    ax.barh(y, values, height=0.56, color=SERIES, edgecolor=SURFACE, linewidth=2, zorder=2)
    ax.set_yticks(y)
    ax.set_yticklabels([label for label, _value in rows], fontsize=10, color=INK, family=FONT)
    ax.set_xlim(0, peak * 2.4)
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.set_xticks([])
    for position, value in zip(y, values):
        text = compact(value) if value >= 100_000 else number(value)
        if show_share:
            text += " · %d%%" % round(value / total * 100)
        ax.text(value + peak * 0.05, position, text, va="center", fontsize=9.5, color=INK_SECONDARY, family=FONT)
    clean_axes(ax)
    ax.spines["bottom"].set_visible(False)
    return ax


def to_png(fig: Figure) -> io.BytesIO:
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=DPI, facecolor=SURFACE)
    buffer.seek(0)
    return buffer

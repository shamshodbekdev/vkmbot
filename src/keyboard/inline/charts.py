from typing import List, Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from filters.callback.charts import ChartsCallback
from filters.callback.youtube_download import YoutubeDownloadCallback
from filters.callback.bulk_download import BulkDownloadCallback
from schemas.playlist import PlaylistTrackSchema
from utils.constants import COUNTRIES, CHARTS_COUNTRY_WINDOW_SIZE

_GLOBAL = next(c for c in COUNTRIES if c[0] == "ZZ")
_NON_GLOBAL = [c for c in COUNTRIES if c[0] != "ZZ"]


class ChartsKeyboard:
    @staticmethod
    def make(
        tracks: List[PlaylistTrackSchema],
        offset: int,
        limit: int,
        total: int,
        current: Optional[str] = "ZZ",
        country_page: int = 0,
    ) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()

        global_code, global_normal, global_selected = _GLOBAL
        builder.row(
            InlineKeyboardButton(
                text=global_selected if current == global_code else global_normal,
                callback_data=ChartsCallback(
                    country_code=global_code,
                    offset=0,
                    limit=limit,
                    country_page=country_page,
                ).pack(),
            )
        )

        page_start = country_page
        page_countries = _NON_GLOBAL[page_start:page_start + CHARTS_COUNTRY_WINDOW_SIZE]
        max_page = max(0, len(_NON_GLOBAL) - CHARTS_COUNTRY_WINDOW_SIZE)

        country_row = []
        if country_page > 0:
            country_row.append(
                InlineKeyboardButton(
                    text="◀",
                    callback_data=ChartsCallback(
                        country_code=current,
                        offset=offset,
                        limit=limit,
                        country_page=country_page - 1,
                    ).pack(),
                )
            )
        for code, normal, selected in page_countries:
            country_row.append(
                InlineKeyboardButton(
                    text=selected if code == current else normal,
                    callback_data=ChartsCallback(
                        country_code=code,
                        offset=0,
                        limit=limit,
                        country_page=country_page,
                    ).pack(),
                )
            )
        if country_page < max_page:
            country_row.append(
                InlineKeyboardButton(
                    text="▶",
                    callback_data=ChartsCallback(
                        country_code=current,
                        offset=offset,
                        limit=limit,
                        country_page=country_page + 1,
                    ).pack(),
                )
            )
        builder.row(*country_row)

        for track in tracks:
            if not track.videoId:
                continue

            artists = ", ".join(a.name for a in track.artists)
            builder.row(
                InlineKeyboardButton(
                    text="%(title)s - %(artists)s" % dict(title=track.title, artists=artists),
                    callback_data=YoutubeDownloadCallback(video_id=track.videoId).pack(),
                )
            )

        cap = min(total, 100)

        nav_row1 = []
        if offset > 0:
            nav_row1.append(
                InlineKeyboardButton(
                    text="⬅️",
                    callback_data=ChartsCallback(
                        country_code=current,
                        offset=offset - limit,
                        limit=limit,
                        country_page=country_page,
                    ).pack(),
                )
            )
        nav_row1.append(
            InlineKeyboardButton(text="⬇️", callback_data=BulkDownloadCallback().pack())
        )
        if offset + limit < cap:
            nav_row1.append(
                InlineKeyboardButton(
                    text="➡️",
                    callback_data=ChartsCallback(
                        country_code=current,
                        offset=offset + limit,
                        limit=limit,
                        country_page=country_page,
                    ).pack(),
                )
            )

        nav_row2 = []
        if offset >= 2 * limit:
            nav_row2.append(
                InlineKeyboardButton(
                    text="⬅️ (2X)",
                    callback_data=ChartsCallback(
                        country_code=current,
                        offset=offset - 2 * limit,
                        limit=limit,
                        country_page=country_page,
                    ).pack(),
                )
            )
        nav_row2.append(
            InlineKeyboardButton(
                text="❌",
                callback_data=ChartsCallback(
                    country_code=current,
                    offset=offset,
                    limit=limit,
                    country_page=country_page,
                    close=True,
                ).pack(),
            )
        )
        if offset + 2 * limit < cap:
            nav_row2.append(
                InlineKeyboardButton(
                    text="➡️ (2X)",
                    callback_data=ChartsCallback(
                        country_code=current,
                        offset=offset + 2 * limit,
                        limit=limit,
                        country_page=country_page,
                    ).pack(),
                )
            )

        builder.row(*nav_row1)
        builder.row(*nav_row2)

        return builder.as_markup()

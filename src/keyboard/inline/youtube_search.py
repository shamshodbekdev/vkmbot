from typing import List
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from filters.callback.youtube_search import YoutubeSearchCallback
from filters.callback.youtube_download import YoutubeDownloadCallback
from filters.callback.bulk_download import BulkDownloadCallback
from filters.callback.close import CloseCallback
from schemas.youtube_search import SongSchema


class YoutubeSearchKeyboard:
    @staticmethod
    def make(
        results: List[SongSchema],
        query: str,
        page: int,
        limit: int,
        has_next: bool,
        has_next_next: bool = False,
    ) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()

        number_buttons = [
            InlineKeyboardButton(
                text=str(page * limit + i + 1),
                callback_data=YoutubeDownloadCallback(
                    video_id=song.videoId,
                ).pack(),
            )
            for i, song in enumerate(results)
        ]
        row_width = max(1, limit // 2)
        for row_start in range(0, len(number_buttons), row_width):
            builder.row(*number_buttons[row_start:row_start + row_width])

        nav_row1 = []
        if page > 0:
            nav_row1.append(
                InlineKeyboardButton(
                    text="⬅️",
                    callback_data=YoutubeSearchCallback(query=query, page=page - 1, limit=limit).pack(),
                )
            )
        nav_row1.append(
            InlineKeyboardButton(text="⬇️", callback_data=BulkDownloadCallback().pack())
        )
        if has_next:
            nav_row1.append(
                InlineKeyboardButton(
                    text="➡️",
                    callback_data=YoutubeSearchCallback(query=query, page=page + 1, limit=limit).pack(),
                )
            )

        nav_row2 = []
        if page >= 2:
            nav_row2.append(
                InlineKeyboardButton(
                    text="⬅️ (2X)",
                    callback_data=YoutubeSearchCallback(query=query, page=page - 2, limit=limit).pack(),
                )
            )
        nav_row2.append(
            InlineKeyboardButton(text="❌", callback_data=CloseCallback().pack())
        )
        if has_next_next:
            nav_row2.append(
                InlineKeyboardButton(
                    text="➡️ (2X)",
                    callback_data=YoutubeSearchCallback(query=query, page=page + 2, limit=limit).pack(),
                )
            )

        builder.row(*nav_row1)
        builder.row(*nav_row2)

        return builder.as_markup()

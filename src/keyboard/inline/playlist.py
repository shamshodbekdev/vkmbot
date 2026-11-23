from typing import List
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.models import AudioPlaylist
from filters.callback.playlist import PlaylistCallback
from filters.callback.youtube_download import YoutubeDownloadCallback
from filters.callback.bulk_download import BulkDownloadCallback
from filters.callback.close import CloseCallback


class PlaylistKeyboard:
    @staticmethod
    def make(items: List[AudioPlaylist], page: int, limit: int, has_next: bool, has_next_next: bool = False) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()

        number_buttons = [
            InlineKeyboardButton(
                text=str(page * limit + i + 1),
                callback_data=YoutubeDownloadCallback(
                    video_id=item.audio.video_id,
                ).pack(),
            )
            for i, item in enumerate(items)
        ]
        row_width = max(1, limit // 2)
        for row_start in range(0, len(number_buttons), row_width):
            builder.row(*number_buttons[row_start:row_start + row_width])

        nav_row1 = []
        if page > 0:
            nav_row1.append(
                InlineKeyboardButton(
                    text="⬅️",
                    callback_data=PlaylistCallback(page=page - 1).pack(),
                )
            )
        nav_row1.append(
            InlineKeyboardButton(text="⬇️", callback_data=BulkDownloadCallback().pack())
        )
        if has_next:
            nav_row1.append(
                InlineKeyboardButton(
                    text="➡️",
                    callback_data=PlaylistCallback(page=page + 1).pack(),
                )
            )

        nav_row2 = []
        if page >= 2:
            nav_row2.append(
                InlineKeyboardButton(
                    text="⬅️ (2X)",
                    callback_data=PlaylistCallback(page=page - 2).pack(),
                )
            )
        nav_row2.append(
            InlineKeyboardButton(text="❌", callback_data=CloseCallback().pack())
        )
        if has_next_next:
            nav_row2.append(
                InlineKeyboardButton(
                    text="➡️ (2X)",
                    callback_data=PlaylistCallback(page=page + 2).pack(),
                )
            )

        builder.row(*nav_row1)
        builder.row(*nav_row2)

        return builder.as_markup()

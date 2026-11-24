from typing import List

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from filters.callback.close import CloseCallback
from filters.callback.first_page import FirstPageCallback
from filters.callback.youtube_download import YoutubeDownloadCallback
from filters.callback.youtube_search import YoutubeSearchCallback
from schemas.youtube_search import SongSchema

NUMBERS_PER_ROW: int = 5


class YoutubeSearchKeyboard:
    """Search results: numbered rows of 5, then ⬅️ ❌ ➡️.

    ⬅️ is always shown; on the first page it only tells the user they are on
    the first page. ➡️ is shown only when there is a next page.
    """

    @staticmethod
    def make(
        results: List[SongSchema],
        query: str,
        page: int,
        limit: int,
        has_next: bool,
        has_next_next: bool = False,  # kept for callers; the 2X buttons were removed
    ) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()

        number_buttons = [
            InlineKeyboardButton(
                text=str(page * limit + i + 1),
                callback_data=YoutubeDownloadCallback(video_id=song.videoId).pack(),
            )
            for i, song in enumerate(results)
        ]
        for row_start in range(0, len(number_buttons), NUMBERS_PER_ROW):
            builder.row(*number_buttons[row_start:row_start + NUMBERS_PER_ROW])

        previous = (
            YoutubeSearchCallback(query=query, page=page - 1, limit=limit)
            if page > 0
            else FirstPageCallback()
        )
        navigation = [InlineKeyboardButton(text="⬅️", callback_data=previous.pack())]
        navigation.append(InlineKeyboardButton(text="❌", callback_data=CloseCallback().pack()))
        if has_next:
            navigation.append(
                InlineKeyboardButton(
                    text="➡️",
                    callback_data=YoutubeSearchCallback(query=query, page=page + 1, limit=limit).pack(),
                )
            )
        builder.row(*navigation)

        return builder.as_markup()

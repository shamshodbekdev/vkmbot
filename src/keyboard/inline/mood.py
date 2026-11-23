from typing import List, Dict
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from filters.callback.mood import MoodMenuCallback, MoodPlaylistsCallback, MoodTracksCallback
from filters.callback.youtube_download import YoutubeDownloadCallback
from filters.callback.bulk_download import BulkDownloadCallback
from filters.callback.close import CloseCallback
from schemas.mood import MoodItemSchema, MoodPlaylistItemSchema
from schemas.playlist import PlaylistTrackSchema
from utils.constants import MOOD_PLAYLIST_PAGE_SIZE, MOOD_PAGE_SIZE


class MoodKeyboard:
    @staticmethod
    def moods(moods: Dict[str, List[MoodItemSchema]], page: int = 0) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        all_items = [item for items in moods.values() for item in items]
        start = page * MOOD_PAGE_SIZE
        end = start + MOOD_PAGE_SIZE
        total = len(all_items)

        for i in range(start, min(end, total), 2):
            builder.row(*[
                InlineKeyboardButton(
                    text=item.title,
                    callback_data=MoodPlaylistsCallback(
                        params=item.params,
                        page=0,
                    ).pack(),
                )
                for item in all_items[i:i + 2]
            ])

        nav = []
        if page > 0:
            nav.append(
                InlineKeyboardButton(
                    text="⬅️",
                    callback_data=MoodMenuCallback(page=page - 1).pack(),
                )
            )
        nav.append(
            InlineKeyboardButton(
                text=str(page + 1),
                callback_data=MoodMenuCallback(page=page).pack(),
            )
        )
        if end < total:
            nav.append(
                InlineKeyboardButton(
                    text="➡️",
                    callback_data=MoodMenuCallback(page=page + 1).pack(),
                )
            )
        builder.row(*nav)
        return builder.as_markup()

    @staticmethod
    def playlists(
        playlists: List[MoodPlaylistItemSchema],
        params: str,
        page: int,
    ) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        start = page * MOOD_PLAYLIST_PAGE_SIZE
        end = start + MOOD_PLAYLIST_PAGE_SIZE
        total = len(playlists)

        for playlist in playlists[start:end]:
            builder.row(
                InlineKeyboardButton(
                    text=playlist.title,
                    callback_data=MoodTracksCallback(
                        playlist_id=playlist.playlistId,
                    ).pack(),
                )
            )

        nav_row1 = []
        if page > 0:
            nav_row1.append(
                InlineKeyboardButton(
                    text="⬅️",
                    callback_data=MoodPlaylistsCallback(params=params, page=page - 1).pack(),
                )
            )
        if end < total:
            nav_row1.append(
                InlineKeyboardButton(
                    text="➡️",
                    callback_data=MoodPlaylistsCallback(params=params, page=page + 1).pack(),
                )
            )

        nav_row2 = []
        if page >= 2:
            nav_row2.append(
                InlineKeyboardButton(
                    text="⬅️ (2X)",
                    callback_data=MoodPlaylistsCallback(params=params, page=page - 2).pack(),
                )
            )
        nav_row2.append(
            InlineKeyboardButton(text="↩️", callback_data=MoodMenuCallback().pack())
        )
        nav_row2.append(
            InlineKeyboardButton(text="❌", callback_data=CloseCallback().pack())
        )
        if end + MOOD_PLAYLIST_PAGE_SIZE < total:
            nav_row2.append(
                InlineKeyboardButton(
                    text="➡️ (2X)",
                    callback_data=MoodPlaylistsCallback(params=params, page=page + 2).pack(),
                )
            )

        if nav_row1:
            builder.row(*nav_row1)
        builder.row(*nav_row2)
        return builder.as_markup()

    @staticmethod
    def tracks(
        tracks: List[PlaylistTrackSchema],
        offset: int,
        limit: int,
        total: int,
    ) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()

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

        nav_row1 = []
        if offset > 0:
            nav_row1.append(
                InlineKeyboardButton(
                    text="⬅️",
                    callback_data=MoodTracksCallback(
                        offset=offset - limit,
                        limit=limit,
                    ).pack(),
                )
            )
        nav_row1.append(
            InlineKeyboardButton(text="⬇️", callback_data=BulkDownloadCallback().pack())
        )
        if offset + limit < total:
            nav_row1.append(
                InlineKeyboardButton(
                    text="➡️",
                    callback_data=MoodTracksCallback(
                        offset=offset + limit,
                        limit=limit,
                    ).pack(),
                )
            )

        nav_row2 = []
        if offset >= 2 * limit:
            nav_row2.append(
                InlineKeyboardButton(
                    text="⬅️ (2X)",
                    callback_data=MoodTracksCallback(
                        offset=offset - 2 * limit,
                        limit=limit,
                    ).pack(),
                )
            )
        nav_row2.append(
            InlineKeyboardButton(text="↩️", callback_data=MoodPlaylistsCallback().pack())
        )
        nav_row2.append(
            InlineKeyboardButton(
                text="❌",
                callback_data=MoodTracksCallback(close=True).pack(),
            )
        )
        if offset + 2 * limit < total:
            nav_row2.append(
                InlineKeyboardButton(
                    text="➡️ (2X)",
                    callback_data=MoodTracksCallback(
                        offset=offset + 2 * limit,
                        limit=limit,
                    ).pack(),
                )
            )

        builder.row(*nav_row1)
        builder.row(*nav_row2)
        return builder.as_markup()

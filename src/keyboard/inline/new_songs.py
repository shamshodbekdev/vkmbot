from typing import List

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.i18n import gettext as _
from aiogram.utils.keyboard import InlineKeyboardBuilder

from filters.callback.new_songs import NewSongsCallback
from filters.callback.youtube_download import YoutubeDownloadCallback
from filters.callback.youtube_link import YoutubeLinkCallback
from schemas.playlist import PlaylistTrackSchema
from schemas.youtube_search import SongSchema
from services.youtube.new_songs import track_label

NEW_SONGS_TITLE: str = "NEW Popular Songs"
_MAX_BUTTON_TEXT: int = 60


class NewSongsKeyboard:
    @staticmethod
    def page(tracks: List[PlaylistTrackSchema], page: int, has_next: bool) -> InlineKeyboardMarkup:
        """One button per song, then ⬅️ / ➡️."""
        builder = InlineKeyboardBuilder()
        for track in tracks:
            label = track_label(track)
            if len(label) > _MAX_BUTTON_TEXT:
                label = label[:_MAX_BUTTON_TEXT - 1] + "…"
            builder.row(InlineKeyboardButton(
                text=label,
                callback_data=NewSongsCallback(action="song", page=page, video_id=track.videoId).pack(),
            ))
        navigation = []
        if page > 0:
            navigation.append(InlineKeyboardButton(
                text="⬅️", callback_data=NewSongsCallback(action="page", page=page - 1).pack(),
            ))
        if has_next:
            navigation.append(InlineKeyboardButton(
                text="➡️", callback_data=NewSongsCallback(action="page", page=page + 1).pack(),
            ))
        if navigation:
            builder.row(*navigation)
        return builder.as_markup()

    @staticmethod
    def versions(video_id: str, songs: List[SongSchema], page: int) -> InlineKeyboardMarkup:
        """🎬 Video, number buttons for each version, ⬅️ back to the list page."""
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(
            text=_("🎬 Video"),
            callback_data=YoutubeLinkCallback(kind="video", video_id=video_id).pack(),
        ))
        if songs:
            builder.row(*[
                InlineKeyboardButton(text=str(i + 1), callback_data=YoutubeDownloadCallback(video_id=song.videoId).pack())
                for i, song in enumerate(songs)
            ])
        builder.row(InlineKeyboardButton(
            text="⬅️ %s" % NEW_SONGS_TITLE,
            callback_data=NewSongsCallback(action="page", page=page).pack(),
        ))
        return builder.as_markup()

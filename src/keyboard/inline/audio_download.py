from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.i18n import gettext as _
from filters.callback.audio_playlist import AudioPlaylistCallback


class AudioDownloadKeyboard:
    @staticmethod
    def make(video_id: str) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text=_("Like"),
                style="success",
                icon_custom_emoji_id="5449505950283078474",
                callback_data=AudioPlaylistCallback(action="like", video_id=video_id).pack(),
            ),
            InlineKeyboardButton(
                text=_("Unlike"),
                style="danger",
                icon_custom_emoji_id="5471954395719539651",
                callback_data=AudioPlaylistCallback(action="unlike", video_id=video_id).pack(),
            ),
        )
        builder.row(
            InlineKeyboardButton(
                text=_("Close"),
                icon_custom_emoji_id="5465665476971471368",
                callback_data=AudioPlaylistCallback(action="close", video_id=video_id).pack(),
            )
        )
        return builder.as_markup()

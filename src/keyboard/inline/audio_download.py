from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.i18n import gettext as _
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.bot_identity import add_to_group_url
from filters.callback.audio_effect import AudioEffectCallback
from filters.callback.audio_playlist import AudioPlaylistCallback


class AudioDownloadKeyboard:
    """Keyboard under a downloaded track.

    Row 1: ❤️ (add to /my playlist; turns into 💔 to remove) and 💾 (get the track as a file)
    Row 2: 🔗 add the bot to a group
    Row 3: audio effects (8D, Concert Hall, Slowed)
    """

    @staticmethod
    def make(video_id: str, like_buttons: bool = True, liked: bool = False) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()

        first_row = []
        if like_buttons:
            first_row.append(
                InlineKeyboardButton(
                    text="💔" if liked else "❤️",
                    callback_data=AudioPlaylistCallback(action="unlike" if liked else "like", video_id=video_id).pack(),
                )
            )
        first_row.append(
            InlineKeyboardButton(
                text="💾",
                callback_data=AudioPlaylistCallback(action="file", video_id=video_id).pack(),
            )
        )
        builder.row(*first_row)

        builder.row(InlineKeyboardButton(text=_("🔗 Add to group"), url=add_to_group_url()))

        builder.row(
            InlineKeyboardButton(
                text=_("🎧 8D"),
                callback_data=AudioEffectCallback(effect="8d", video_id=video_id).pack(),
            ),
            InlineKeyboardButton(
                text=_("🏛 Concert Hall"),
                callback_data=AudioEffectCallback(effect="concert", video_id=video_id).pack(),
            ),
            InlineKeyboardButton(
                text=_("🐢 Slowed"),
                callback_data=AudioEffectCallback(effect="slowed", video_id=video_id).pack(),
            ),
        )
        return builder.as_markup()

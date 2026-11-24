from typing import Dict, Optional

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.i18n import gettext as _
from aiogram.utils.keyboard import InlineKeyboardBuilder

from filters.callback.youtube_link import YoutubeLinkCallback
from filters.callback.youtube_quality import YoutubeQualityCallback


def quality_label(quality: str) -> str:
    return "🎬 4K" if quality == "2160" else "🎬 %sp" % quality


class YoutubeLinkKeyboard:
    @staticmethod
    def make(video_id: str, qualities: Optional[Dict[str, int]] = None) -> InlineKeyboardMarkup:
        """Resolution grid (only resolutions the video has) + a full-width "🎵 Audio" button.

        Without resolution info (should not happen) the old "📼 Video" / "🎧 Audio" pair is shown.
        """
        builder = InlineKeyboardBuilder()
        if not qualities:
            builder.row(
                InlineKeyboardButton(
                    text=_("📼 Video"),
                    callback_data=YoutubeLinkCallback(kind="video", video_id=video_id).pack(),
                ),
                InlineKeyboardButton(
                    text=_("🎧 Audio"),
                    callback_data=YoutubeLinkCallback(kind="audio", video_id=video_id).pack(),
                ),
            )
            return builder.as_markup()

        buttons = [
            InlineKeyboardButton(
                text=quality_label(quality),
                callback_data=YoutubeQualityCallback(platform="yt", quality=quality, video_id=video_id).pack(),
            )
            for quality in sorted(qualities, key=int)
        ]
        for start in range(0, len(buttons), 3):
            builder.row(*buttons[start:start + 3])
        builder.row(InlineKeyboardButton(
            text=_("🎵 Audio"),
            callback_data=YoutubeQualityCallback(platform="yt", quality="audio", video_id=video_id).pack(),
        ))
        return builder.as_markup()

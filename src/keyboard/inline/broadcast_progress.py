from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.i18n import gettext as _
from filters.callback.broadcast_progress import BroadcastProgressCallback
from utils.constants import BROADCAST_PROGRESS_ICONS


class BroadcastProgressKeyboard:
    @staticmethod
    def make(
        broadcast_id: str,
        paused: bool = False,
        finished: bool = False,
        stopped: bool = False,
    ) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        if not finished and not stopped:
            toggle_action = "resume" if paused else "pause"
            toggle_text = _("Resume") if paused else _("Pause")
            toggle_icon = next(icon for flag, icon in BROADCAST_PROGRESS_ICONS if flag == paused)
            builder.row(
                InlineKeyboardButton(
                    text=toggle_text,
                    icon_custom_emoji_id=toggle_icon,
                    callback_data=BroadcastProgressCallback(
                        broadcast_id=broadcast_id,
                        action=toggle_action,
                    ).pack(),
                ),
            )
            builder.row(
                InlineKeyboardButton(
                    text=_("Stop"),
                    icon_custom_emoji_id="5467890025217661107",
                    callback_data=BroadcastProgressCallback(
                        broadcast_id=broadcast_id,
                        action="stop",
                    ).pack(),
                ),
            )
        builder.row(
            InlineKeyboardButton(
                text=_("View progress"),
                icon_custom_emoji_id="5424885441100782420",
                callback_data=BroadcastProgressCallback(
                    broadcast_id=broadcast_id,
                    action="view",
                ).pack(),
            )
        )
        builder.adjust(1)
        return builder.as_markup()

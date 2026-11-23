import humanize
from typing import List
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.i18n import gettext as _
from database.models.broadcast import BroadcastRecord
from filters.callback.broadcast_history import BroadcastHistoryCallback
from utils.constants.broadcast import BROADCAST_PAGE_SIZE as PAGE_SIZE


class BroadcastHistoryKeyboard:
    @staticmethod
    def menu() -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text=_("Broadcast history"),
                icon_custom_emoji_id="5465143921912846619",
                callback_data=BroadcastHistoryCallback(action="list", page=0).pack(),
            )
        )
        builder.row(
            InlineKeyboardButton(
                text=_("New broadcast"),
                icon_custom_emoji_id="5226945370684140473",
                callback_data=BroadcastHistoryCallback(action="new").pack(),
            )
        )
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def list(records: List[BroadcastRecord], page: int, total: int) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        for record in records:
            label = record.created_at.strftime("%d.%m.%Y %H:%M")
            builder.row(
                InlineKeyboardButton(
                    text="%(label)s  —  %(success)s / %(audience)s" % dict(
                        label=label,
                        success=humanize.intcomma(record.success),
                        audience=humanize.intcomma(record.audience),
                    ),
                    icon_custom_emoji_id="5424885441100782420",
                    callback_data=BroadcastHistoryCallback(
                        action="select",
                        broadcast_id=str(record.id),
                        page=page,
                    ).pack(),
                )
            )
        total_pages = max((total + PAGE_SIZE - 1) // PAGE_SIZE, 1)
        nav = []
        if page > 0:
            nav.append(
                InlineKeyboardButton(
                    text="◀",
                    callback_data=BroadcastHistoryCallback(action="list", page=page - 1).pack(),
                )
            )
        nav.append(
            InlineKeyboardButton(
                text="%(page)s / %(total)s" % dict(page=page + 1, total=total_pages),
                callback_data=BroadcastHistoryCallback(action="noop").pack(),
            )
        )
        if (page + 1) * PAGE_SIZE < total:
            nav.append(
                InlineKeyboardButton(
                    text="▶",
                    callback_data=BroadcastHistoryCallback(action="list", page=page + 1).pack(),
                )
            )
        if nav:
            builder.row(*nav)
        builder.row(
            InlineKeyboardButton(
                text="⬅️",
                callback_data=BroadcastHistoryCallback(action="menu").pack(),
            )
        )
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def detail(broadcast_id: str, page: int) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="⬅️",
                callback_data=BroadcastHistoryCallback(action="list", page=page).pack(),
            )
        )
        builder.adjust(1)
        return builder.as_markup()

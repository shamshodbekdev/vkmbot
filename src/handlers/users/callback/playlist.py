from contextlib import suppress
from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.i18n import gettext as _
from database.models import User, AudioPlaylist, UserPreferences
from filters.callback.playlist import PlaylistCallback
from keyboard.inline import PlaylistKeyboard
from utils.formatters import build_playlist

router = Router()


@router.callback_query(PlaylistCallback.filter())
async def playlist_callback_handler(
    callback: CallbackQuery,
    callback_data: PlaylistCallback,
    user: User,
    state: FSMContext,
) -> None:
    prefs, __ = await UserPreferences.get_or_create(user=user)
    limit = prefs.max_results
    page = max(callback_data.page, 0)

    total = await AudioPlaylist.filter(user=user).count()

    if not total:
        await callback.answer(_("Your playlist is empty."))
        return

    items = list(
        await AudioPlaylist.filter(user=user)
        .order_by("-created_at")
        .prefetch_related("audio")
        .offset(page * limit)
        .limit(limit + 1)
    )

    has_next = len(items) > limit
    has_next_next = (page + 2) * limit < total
    if has_next:
        items = items[:limit]

    await state.update_data(bulk_video_ids=[item.audio.video_id for item in items])

    if not items:
        await callback.answer(_("Your playlist is empty."))
        return

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=build_playlist(items=items, page=page, limit=limit, total=total),
            reply_markup=PlaylistKeyboard.make(
                items=items,
                page=page,
                limit=limit,
                has_next=has_next,
                has_next_next=has_next_next,
            ),
        )
    await callback.answer()

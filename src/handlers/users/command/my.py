from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.i18n import gettext as _
from database.models import User, AudioPlaylist, UserPreferences
from keyboard.inline import PlaylistKeyboard
from utils.formatters import build_playlist

router = Router()


@router.message(Command("my"))
async def my_handler(message: Message, user: User, state: FSMContext) -> None:
    prefs, __ = await UserPreferences.get_or_create(user=user)
    limit = prefs.max_results
    page = 0

    total = await AudioPlaylist.filter(user=user).count()

    if not total:
        await message.answer(text=_("Your playlist is empty."))
        return

    items = list(
        await AudioPlaylist.filter(user=user)
        .order_by("-created_at")
        .prefetch_related("audio")
        .offset(0)
        .limit(limit + 1)
    )

    has_next = len(items) > limit
    has_next_next = (page + 2) * limit < total
    if has_next:
        items = items[:limit]

    await state.update_data(bulk_video_ids=[item.audio.video_id for item in items])

    await message.answer(
        text=build_playlist(items=items, page=page, limit=limit, total=total),
        reply_markup=PlaylistKeyboard.make(items=items, page=page, limit=limit, has_next=has_next, has_next_next=has_next_next),
    )

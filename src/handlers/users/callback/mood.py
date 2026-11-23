from contextlib import suppress
from html import escape

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.utils.i18n import gettext as _
from filters.callback.mood import MoodMenuCallback, MoodPlaylistsCallback, MoodTracksCallback
from services.youtube.mood import YouTubeMood
from services.youtube.playlist import YouTubePlaylist
from keyboard.inline import MoodKeyboard
from states import MoodState
from utils.helpers import safe_delete

router = Router()


async def _edit(callback: CallbackQuery, text: str, reply_markup: InlineKeyboardMarkup) -> None:
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(text=text, reply_markup=reply_markup)


@router.callback_query(MoodMenuCallback.filter())
async def mood_menu_callback_handler(
    callback: CallbackQuery,
    callback_data: MoodMenuCallback,
    state: FSMContext,
) -> None:
    moods = await YouTubeMood.moods()
    if not moods:
        await callback.answer(_("No moods available."))
        return
    await state.set_state(None)
    await _edit(callback, _("Select a mood:"), MoodKeyboard.moods(moods=moods, page=max(callback_data.page, 0)))
    await callback.answer()


@router.callback_query(MoodPlaylistsCallback.filter())
async def mood_playlists_callback_handler(
    callback: CallbackQuery,
    callback_data: MoodPlaylistsCallback,
    state: FSMContext,
) -> None:
    if callback_data.params:
        params = callback_data.params
    else:
        data = await state.get_data()
        params = data.get("params", "")
    if not params:
        await callback.answer(_("No moods available."))
        return

    playlists = await YouTubeMood.playlists(params=params)
    if not playlists:
        await callback.answer(_("No playlists found."))
        return

    await state.set_state(MoodState.PLAYLISTS)
    await state.update_data(params=params, page=callback_data.page)

    await _edit(
        callback,
        _("Select a playlist:"),
        MoodKeyboard.playlists(playlists=playlists, params=params, page=max(callback_data.page, 0)),
    )
    await callback.answer()


@router.callback_query(MoodTracksCallback.filter())
async def mood_tracks_callback_handler(
    callback: CallbackQuery,
    callback_data: MoodTracksCallback,
    state: FSMContext,
) -> None:
    if callback_data.close:
        await safe_delete(callback.message)
        await state.set_state(None)
        await callback.answer()
        return

    data = await state.get_data()
    if callback_data.playlist_id:
        playlist_id = callback_data.playlist_id
        params = data.get("params", "")
        mood_page = data.get("page", 0)
        await state.set_state(MoodState.TRACKS)
        await state.update_data(playlist_id=playlist_id, params=params, mood_page=mood_page)
    else:
        playlist_id = data.get("playlist_id", "")
        params = data.get("params", "")
        mood_page = data.get("mood_page", 0)

    playlist = await YouTubePlaylist.get(playlist_id=playlist_id, limit=100) if playlist_id else None
    if not playlist or not playlist.tracks:
        await callback.answer(_("No tracks found."))
        return

    tracks = playlist.tracks
    offset = max(callback_data.offset, 0)
    limit = callback_data.limit if callback_data.limit > 0 else 10
    page_tracks = tracks[offset:offset + limit]
    total = len(tracks)

    await state.update_data(bulk_video_ids=[track.videoId for track in page_tracks if track.videoId])

    await _edit(
        callback,
        escape(playlist.title),
        MoodKeyboard.tracks(tracks=page_tracks, offset=offset, limit=limit, total=total),
    )
    await callback.answer()


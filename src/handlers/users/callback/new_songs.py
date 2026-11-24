from contextlib import suppress
from html import escape

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery
from aiogram.utils.i18n import gettext as _

from filters.callback.new_songs import NewSongsCallback
from keyboard.inline.new_songs import NEW_SONGS_TITLE, NewSongsKeyboard
from services.youtube.new_songs import NewSongs, track_label
from utils.constants.youtube import NEW_SONGS_PAGE_SIZE

router = Router()


async def _show_page(callback: CallbackQuery, page: int) -> None:
    tracks = await NewSongs.tracks()
    if not tracks:
        await callback.answer(_("No new songs available right now. Please try again later."), show_alert=True)
        return
    last_page = (len(tracks) - 1) // NEW_SONGS_PAGE_SIZE
    page = min(max(page, 0), last_page)
    start = page * NEW_SONGS_PAGE_SIZE
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text="<b>%s</b>" % NEW_SONGS_TITLE,
            reply_markup=NewSongsKeyboard.page(
                tracks=tracks[start:start + NEW_SONGS_PAGE_SIZE], page=page, has_next=page < last_page,
            ),
        )
    await callback.answer()


@router.callback_query(NewSongsCallback.filter(F.action == "page"))
async def new_songs_page_handler(callback: CallbackQuery, callback_data: NewSongsCallback) -> None:
    await _show_page(callback, callback_data.page)


@router.callback_query(NewSongsCallback.filter(F.action == "song"))
async def new_songs_song_handler(callback: CallbackQuery, callback_data: NewSongsCallback) -> None:
    tracks = await NewSongs.tracks()
    track = next((t for t in tracks if t.videoId == callback_data.video_id), None)
    if track is None:
        # The daily chart changed since this message was sent: show the fresh list.
        await callback.answer(_("The list has been updated. Here is the latest one."), show_alert=True)
        await _show_page(callback, 0)
        return

    versions = await NewSongs.versions(track)
    lines = ["<b>%s</b>" % escape(track_label(track)), ""]
    for i, song in enumerate(versions):
        artists = ", ".join(a.name for a in song.artists if a.name)
        lines.append("<b>%d.</b> %s - %s %s" % (
            i + 1, escape(artists), escape(song.title), escape(song.duration or ""),
        ))
    if not versions:
        lines.append(_("No other versions found."))
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text="\n".join(lines).strip(),
            reply_markup=NewSongsKeyboard.versions(
                video_id=track.videoId, songs=versions, page=callback_data.page,
            ),
        )
    await callback.answer()

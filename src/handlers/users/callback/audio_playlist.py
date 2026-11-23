from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.i18n import gettext as _
from database.models import User, AudioPlaylist, YoutubeAudio
from filters.callback.audio_playlist import AudioPlaylistCallback
from utils.helpers import safe_delete

router = Router()


@router.callback_query(AudioPlaylistCallback.filter(F.action == "like"))
async def audio_playlist_like_handler(
    callback: CallbackQuery,
    callback_data: AudioPlaylistCallback,
    user: User,
) -> None:
    audio = await YoutubeAudio.get_or_none(video_id=callback_data.video_id)
    if not audio:
        await callback.answer(_("Track not found."), show_alert=True)
        return
    await AudioPlaylist.get_or_create(user=user, audio=audio)
    await callback.answer(_("Saved to playlist"), show_alert=False)


@router.callback_query(AudioPlaylistCallback.filter(F.action == "unlike"))
async def audio_playlist_unlike_handler(
    callback: CallbackQuery,
    callback_data: AudioPlaylistCallback,
    user: User,
) -> None:
    audio = await YoutubeAudio.filter(video_id=callback_data.video_id).first()
    if audio:
        await AudioPlaylist.filter(user=user, audio=audio).delete()
    await callback.answer(_("Removed from playlist"), show_alert=False)


@router.callback_query(AudioPlaylistCallback.filter(F.action == "close"))
async def audio_playlist_close_handler(callback: CallbackQuery) -> None:
    await safe_delete(callback.message)
    await callback.answer()

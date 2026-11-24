from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.utils.i18n import gettext as _

from keyboard.inline.new_songs import NEW_SONGS_TITLE, NewSongsKeyboard
from services.youtube.new_songs import NewSongs
from utils.constants.youtube import NEW_SONGS_PAGE_SIZE

router = Router()


@router.message(Command("new"))
async def new_songs_handler(message: Message) -> None:
    tracks = await NewSongs.tracks()
    if not tracks:
        await message.answer(text=_("No new songs available right now. Please try again later."))
        return
    await message.answer(
        text="<b>%s</b>" % NEW_SONGS_TITLE,
        reply_markup=NewSongsKeyboard.page(
            tracks=tracks[:NEW_SONGS_PAGE_SIZE], page=0, has_next=len(tracks) > NEW_SONGS_PAGE_SIZE,
        ),
    )

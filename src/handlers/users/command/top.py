from html import escape

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.utils.i18n import gettext as _

from keyboard.inline import ChartsKeyboard
from services.youtube.charts import YouTubeCharts
from utils.constants import YOUTUBE_PAGE_SIZE

router = Router()


@router.message(Command("top"))
async def top_handler(message: Message, state: FSMContext) -> None:
    country_code = "ZZ"
    limit = YOUTUBE_PAGE_SIZE

    playlist = await YouTubeCharts.get_playlist(country=country_code)
    if not playlist or not playlist.tracks:
        await message.answer(text=_("No charts available."))
        return

    page_tracks = playlist.tracks[:limit]
    await state.update_data(bulk_video_ids=[track.videoId for track in page_tracks if track.videoId])

    await message.answer(
        text=escape(playlist.title),
        reply_markup=ChartsKeyboard.make(
            tracks=page_tracks,
            offset=0,
            limit=limit,
            total=len(playlist.tracks),
            current=country_code,
            country_page=0,
        ),
    )

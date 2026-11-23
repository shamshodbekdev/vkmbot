from contextlib import suppress
from html import escape

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from aiogram.utils.i18n import gettext as _

from filters.callback import ChartsCallback
from keyboard.inline import ChartsKeyboard
from services.youtube.charts import YouTubeCharts
from utils.constants import COUNTRIES
from utils.helpers import safe_delete

router = Router()

_COUNTRY_CODES = {code for code, _name, _selected in COUNTRIES}


@router.callback_query(ChartsCallback.filter())
async def charts_callback_handler(
    callback: CallbackQuery,
    callback_data: ChartsCallback,
    state: FSMContext,
) -> None:
    if callback_data.close:
        await safe_delete(callback.message)
        await callback.answer()
        return

    country_code = callback_data.country_code if callback_data.country_code in _COUNTRY_CODES else "ZZ"
    offset = max(callback_data.offset, 0)
    limit = callback_data.limit if callback_data.limit > 0 else 10

    playlist = await YouTubeCharts.get_playlist(country=country_code)
    if not playlist or not playlist.tracks:
        await callback.answer(_("No charts available."), show_alert=True)
        return

    page_tracks = playlist.tracks[offset:offset + limit]
    await state.update_data(bulk_video_ids=[track.videoId for track in page_tracks if track.videoId])

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=escape(playlist.title),
            reply_markup=ChartsKeyboard.make(
                tracks=page_tracks,
                offset=offset,
                limit=limit,
                total=len(playlist.tracks),
                current=country_code,
                country_page=max(callback_data.country_page, 0),
            ),
        )
    await callback.answer()

from contextlib import suppress
from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from aiogram.utils.i18n import gettext as _

from database.models import User, UserPreferences
from filters.callback import SuggestionCallback
from keyboard.inline import YoutubeSearchKeyboard
from services.youtube.search import YouTubeSearch
from utils.formatters import build_search_results
from utils.helpers import load_query, store_query

router = Router()


@router.callback_query(SuggestionCallback.filter())
async def suggestion_callback_handler(
    callback: CallbackQuery,
    callback_data: SuggestionCallback,
    user: User,
    state: FSMContext,
) -> None:
    query = await load_query(callback_data.query)
    if not query:
        await callback.answer(_("This search has expired. Please send your query again."), show_alert=True)
        return

    prefs, __ = await UserPreferences.get_or_create(user=user)
    limit = prefs.max_results

    results = [
        song for song in await YouTubeSearch.search(query=query, limit=2 * limit + 1, offset=0)
        if song.videoId
    ]
    if not results:
        with suppress(TelegramBadRequest):
            await callback.message.edit_text(text=_("No results found."))
        await callback.answer()
        return

    has_next = len(results) > limit
    has_next_next = len(results) > 2 * limit
    results = results[:limit]

    await state.update_data(bulk_video_ids=[song.videoId for song in results])

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=build_search_results(results=results, page=0, limit=limit),
            reply_markup=YoutubeSearchKeyboard.make(
                results=results,
                query=await store_query(query),
                page=0,
                limit=limit,
                has_next=has_next,
                has_next_next=has_next_next,
            ),
        )
    await callback.answer()

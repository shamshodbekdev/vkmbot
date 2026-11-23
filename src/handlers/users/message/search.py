from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.utils.i18n import gettext as _

from database.models import User, UserPreferences
from filters.common import OnlyPrivate
from keyboard.inline import SuggestionsKeyboard, YoutubeSearchKeyboard
from services.youtube.search import YouTubeSearch
from utils.formatters import build_search_results
from utils.helpers import store_query

router = Router()


@router.message(F.text, ~F.text.startswith("/"), OnlyPrivate())
async def search_handler(message: Message, user: User, state: FSMContext) -> None:
    query = message.text.strip()
    if not query:
        return

    prefs, _created = await UserPreferences.get_or_create(user=user)
    limit = prefs.max_results

    results = [
        song for song in await YouTubeSearch.search(query=query, limit=2 * limit + 1, offset=0)
        if song.videoId
    ]

    if not results:
        suggestions = await YouTubeSearch.suggestions(query=query)
        suggestions = [text for text in suggestions if isinstance(text, str) and text.strip()][:limit]
        if not suggestions:
            await message.answer(text=_("No results found."))
            return
        await message.answer(
            text=_("No results found. Did you mean:"),
            reply_markup=SuggestionsKeyboard.make(
                suggestions=[(text[:64], await store_query(text)) for text in suggestions],
            ),
        )
        return

    has_next = len(results) > limit
    has_next_next = len(results) > 2 * limit
    results = results[:limit]

    await state.update_data(bulk_video_ids=[song.videoId for song in results])

    await message.answer(
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

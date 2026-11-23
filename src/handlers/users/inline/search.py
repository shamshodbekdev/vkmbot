from aiogram import Router
from aiogram.types import InlineQuery, InlineQueryResultCachedAudio, InlineQueryResultsButton
from aiogram.utils.i18n import gettext as _
from tortoise.expressions import Q
from tortoise.functions import Count

from core.config import config
from database.models import YoutubeAudio, AudioPlaylist
from utils.constants import INLINE_SEARCH_LIMIT

router = Router()


@router.inline_query()
async def inline_search_handler(query: InlineQuery) -> None:
    text = query.query.strip()

    if text:
        audios = await YoutubeAudio.filter(
            Q(title__icontains=text) | Q(performer__icontains=text)
        ).limit(INLINE_SEARCH_LIMIT)
    else:
        top_ids = list(
            await AudioPlaylist
            .annotate(uses=Count("id"))
            .group_by("audio_id")
            .order_by("-uses")
            .limit(INLINE_SEARCH_LIMIT)
            .values_list("audio_id", flat=True)
        )
        if top_ids:
            audio_map = dict(
                (a.id, a) for a in await YoutubeAudio.filter(id__in=top_ids)
            )
            audios = [audio_map[uid] for uid in top_ids if uid in audio_map]
        else:
            audios = await YoutubeAudio.all().order_by("-created_at").limit(INLINE_SEARCH_LIMIT)

    results = [
        InlineQueryResultCachedAudio(
            id=str(audio.id),
            audio_file_id=audio.file_id,
            caption=_(
                "Find any music you want quickly and easily via %(username_bot)s!"
            ) % dict(username_bot=config.telegram_username),
        )
        for audio in audios
    ]

    await query.answer(
        results=results,
        button=InlineQueryResultsButton(
            text=_("Inline search"),
            start_parameter="inline",
        ),
        cache_time=0,
        is_personal=True,
    )

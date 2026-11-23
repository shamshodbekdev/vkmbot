from html import escape
from typing import List
from aiogram.utils.i18n import gettext as _
from schemas.youtube_search import SongSchema


def build_search_results(results: List[SongSchema], page: int, limit: int) -> str:
    lines = []
    for index, song in enumerate(results):
        artists = ", ".join(a.name for a in song.artists)
        lines.append("<b>%(num)s.</b> <i>%(title)s – %(artists)s %(duration)s</i>" % dict(
            num=page * limit + index + 1,
            title=escape(song.title),
            artists=escape(artists),
            duration=escape(song.duration or "—"),
        ))
    return _("<b>Results</b>:\n\n%(results)s") % dict(results="\n".join(lines))


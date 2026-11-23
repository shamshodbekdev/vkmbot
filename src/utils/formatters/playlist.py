from html import escape
from typing import List
from aiogram.utils.i18n import gettext as _
from database.models import AudioPlaylist


def build_playlist(items: List[AudioPlaylist], page: int, limit: int, total: int) -> str:
    lines = []
    for index, item in enumerate(items):
        lines.append(
            "<b>%(num)s.</b> <i>%(title)s \u2013 %(performer)s</i>" % dict(
                num=page * limit + index + 1,
                title=escape(item.audio.title),
                performer=escape(item.audio.performer),
            )
        )
    page_start = page * limit + 1
    page_end = page * limit + len(items)
    return _("<b>Your playlist:</b> %(page_start)d-%(page_end)d of %(total)d\n\n%(items)s") % dict(
        page_start=page_start,
        page_end=page_end,
        total=total,
        items="\n".join(lines),
    )

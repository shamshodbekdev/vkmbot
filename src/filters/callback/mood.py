from aiogram.filters.callback_data import CallbackData
from utils.constants import YOUTUBE_PAGE_SIZE


class MoodMenuCallback(CallbackData, prefix="mmenu"):
    page: int = 0


class MoodPlaylistsCallback(CallbackData, prefix="mpls"):
    params: str = ""
    page: int = 0


class MoodTracksCallback(CallbackData, prefix="mtrk"):
    playlist_id: str = ""
    offset: int = 0
    limit: int = YOUTUBE_PAGE_SIZE
    close: bool = False

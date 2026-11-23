from aiogram.filters.callback_data import CallbackData
from utils.constants import YOUTUBE_PAGE_SIZE


class YoutubeSearchCallback(CallbackData, prefix="yt"):
    query: str
    page: int = 0
    limit: int = YOUTUBE_PAGE_SIZE

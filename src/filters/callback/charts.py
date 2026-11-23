from aiogram.filters.callback_data import CallbackData
from utils.constants import YOUTUBE_PAGE_SIZE


class ChartsCallback(CallbackData, prefix="charts"):
    country_code: str
    offset: int = 0
    limit: int = YOUTUBE_PAGE_SIZE
    close: bool = False
    country_page: int = 0

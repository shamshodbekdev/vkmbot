from aiogram.filters.callback_data import CallbackData


class PlaylistCallback(CallbackData, prefix="plt"):
    page: int = 0

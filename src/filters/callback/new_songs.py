from aiogram.filters.callback_data import CallbackData


class NewSongsCallback(CallbackData, prefix="new"):
    action: str  # "page" | "song"
    page: int = 0
    video_id: str = ""

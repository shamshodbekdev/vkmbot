from aiogram.filters.callback_data import CallbackData


class AudioPlaylistCallback(CallbackData, prefix="apl"):
    action: str
    video_id: str

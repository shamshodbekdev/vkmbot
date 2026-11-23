from aiogram.filters.callback_data import CallbackData


class VideoRecognizeCallback(CallbackData, prefix="vrec"):
    action: str

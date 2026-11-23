from aiogram.filters.callback_data import CallbackData


class YoutubeDownloadCallback(CallbackData, prefix="ytd"):
    video_id: str

from aiogram.filters.callback_data import CallbackData


class YoutubeLinkCallback(CallbackData, prefix="ytl"):
    kind: str  # "video" | "audio"
    video_id: str

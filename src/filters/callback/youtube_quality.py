from aiogram.filters.callback_data import CallbackData


class YoutubeQualityCallback(CallbackData, prefix="dl"):
    """``dl:yt:720:<video_id>`` downloads that resolution, ``dl:yt:audio:<video_id>`` the audio."""

    platform: str  # "yt"
    quality: str  # "360" ... "2160" | "audio"
    video_id: str

from aiogram.filters.callback_data import CallbackData


class AudioEffectCallback(CallbackData, prefix="fx"):
    effect: str
    video_id: str

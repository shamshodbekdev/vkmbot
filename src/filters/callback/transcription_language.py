from aiogram.filters.callback_data import CallbackData


class TranscriptionLanguageCallback(CallbackData, prefix="trl"):
    locale: str

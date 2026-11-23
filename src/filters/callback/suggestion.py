from aiogram.filters.callback_data import CallbackData


class SuggestionCallback(CallbackData, prefix="sug"):
    query: str

from aiogram.filters.callback_data import CallbackData


class FirstPageCallback(CallbackData, prefix="first"):
    """⬅️ on the first page of results: only shows a notice."""

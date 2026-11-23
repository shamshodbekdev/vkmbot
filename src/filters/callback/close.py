from aiogram.filters.callback_data import CallbackData


class CloseCallback(CallbackData, prefix="cls"):
    """Field-less callback: the close button carries no data."""

from aiogram.filters.callback_data import CallbackData


class ReloadCallback(CallbackData, prefix="reload"):
    action: str

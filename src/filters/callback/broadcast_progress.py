from aiogram.filters.callback_data import CallbackData


class BroadcastProgressCallback(CallbackData, prefix="bc_progress"):
    broadcast_id: str
    action: str = "view"

from aiogram.filters.callback_data import CallbackData

class AdminCallback(CallbackData, prefix="adm"):
    action: str
    admin_id: int | None = None

from typing import Optional
from aiogram.filters.callback_data import CallbackData


class BroadcastModeCallback(CallbackData, prefix="bc_mode"):
    mode: str
    action: Optional[str] = "select"

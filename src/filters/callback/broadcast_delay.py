from typing import Optional
from aiogram.filters.callback_data import CallbackData


class BroadcastDelayCallback(CallbackData, prefix="bc_delay"):
    seconds: int
    action: Optional[str] = "select"

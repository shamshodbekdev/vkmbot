from aiogram.filters.callback_data import CallbackData
from typing import Optional


class BroadcastHistoryCallback(CallbackData, prefix="bh"):
    action: str
    broadcast_id: Optional[str] = None
    page: Optional[int] = 0

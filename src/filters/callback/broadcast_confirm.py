from typing import Optional
from aiogram.filters.callback_data import CallbackData


class BroadcastConfirmCallback(CallbackData, prefix="bc_confirm"):
    action: Optional[str] = "confirm"

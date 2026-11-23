from typing import Optional
from aiogram.filters.callback_data import CallbackData

class UserManageCallback(CallbackData, prefix="usr"):
    action: str
    user_id: int
    duration: Optional[int] = None

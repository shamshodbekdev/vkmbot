from typing import Optional
from aiogram.filters.callback_data import CallbackData


class BroadcastChatTypeCallback(CallbackData, prefix="bc_chat"):
    chat_type: str
    action: Optional[str] = "toggle"

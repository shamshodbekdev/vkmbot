from typing import Optional
from aiogram.filters.callback_data import CallbackData


class BroadcastLanguageCallback(CallbackData, prefix="bc_lang"):
    language_code: str
    action: Optional[str] = "toggle"

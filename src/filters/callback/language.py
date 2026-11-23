from typing import Optional
from aiogram.filters.callback_data import CallbackData

class LanguageCallback(CallbackData, prefix="language"):
    language_code: str = "en"
    action: Optional[str] = "select"
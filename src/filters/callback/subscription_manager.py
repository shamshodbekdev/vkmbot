from typing import Optional
from aiogram.filters.callback_data import CallbackData


class SubscriptionCallback(CallbackData, prefix="sub"):
    action: str
    subscription_id: Optional[str] = None


class SubscriptionSetupCallback(CallbackData, prefix="sub_setup"):
    action: str

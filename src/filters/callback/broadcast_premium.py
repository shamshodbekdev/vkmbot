from aiogram.filters.callback_data import CallbackData


class BroadcastPremiumCallback(CallbackData, prefix="bpr"):
    is_premium: bool

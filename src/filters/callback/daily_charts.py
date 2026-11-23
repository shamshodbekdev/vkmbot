from aiogram.filters.callback_data import CallbackData


class DailyChartsCallback(CallbackData, prefix="dcharts"):
    step: str = "menu"
    country_code: str = ""
    page: int = 0

from typing import Optional, Dict
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.i18n import gettext as _
from filters.callback.daily_charts import DailyChartsCallback
from filters.callback.settings import SettingsCallback
from utils.constants import DAILY_CHARTS_COUNTRIES, DAILY_CHARTS_PAGE_SIZE, DAILY_CHARTS_HOUR, DAILY_CHARTS_MINUTE


class DailyChartsKeyboard:
    @staticmethod
    def menu(schedule: Optional[Dict] = None) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        if schedule:
            country_code = schedule.get("country_code", "ZZ")
            name = next((n for c, n in DAILY_CHARTS_COUNTRIES if c == country_code), country_code)
            time_str = "%02d:%02d" % (DAILY_CHARTS_HOUR, DAILY_CHARTS_MINUTE)
            builder.row(
                InlineKeyboardButton(
                    text=_("Active: %(flag)s at %(time)s") % dict(flag=name, time=time_str),
                    callback_data=DailyChartsCallback(step="country", page=0).pack(),
                )
            )
            builder.row(
                InlineKeyboardButton(
                    text=_("Disable daily charts"),
                    callback_data=DailyChartsCallback(step="cancel").pack(),
                )
            )
        else:
            builder.row(
                InlineKeyboardButton(
                    text=_("Choose country"),
                    callback_data=DailyChartsCallback(step="country", page=0).pack(),
                )
            )
        builder.row(
            InlineKeyboardButton(
                text="↩️",
                callback_data=SettingsCallback(action="back").pack(),
            )
        )
        return builder.as_markup()

    @staticmethod
    def country(current: str = "", country_page: int = 0) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()

        total = len(DAILY_CHARTS_COUNTRIES)
        start = country_page * DAILY_CHARTS_PAGE_SIZE
        page_countries = DAILY_CHARTS_COUNTRIES[start:start + DAILY_CHARTS_PAGE_SIZE]

        for code, name in page_countries:
            label = name + " ✅" if code == current else name
            builder.row(
                InlineKeyboardButton(
                    text=label,
                    callback_data=DailyChartsCallback(
                        step="set",
                        country_code=code,
                        page=country_page,
                    ).pack(),
                )
            )

        nav = []
        if country_page > 0:
            nav.append(
                InlineKeyboardButton(
                    text="⬅️",
                    callback_data=DailyChartsCallback(
                        step="country",
                        country_code=current,
                        page=country_page - 1,
                    ).pack(),
                )
            )
        if start + DAILY_CHARTS_PAGE_SIZE < total:
            nav.append(
                InlineKeyboardButton(
                    text="➡️",
                    callback_data=DailyChartsCallback(
                        step="country",
                        country_code=current,
                        page=country_page + 1,
                    ).pack(),
                )
            )
        if nav:
            builder.row(*nav)

        builder.row(
            InlineKeyboardButton(
                text="↩️",
                callback_data=DailyChartsCallback(step="menu").pack(),
            )
        )
        return builder.as_markup()

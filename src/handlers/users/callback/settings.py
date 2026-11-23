from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.i18n import gettext as _
from core.cache import cache
from services.daily_charts import daily_charts_cache_key
from utils.constants import MAX_RESULTS_CYCLE
from utils.helpers import safe_delete
from database.models import User, UserPreferences
from filters.callback import SettingsCallback
from keyboard.inline import LanguageKeyboard, SettingsKeyboard
from keyboard.inline.daily_charts import DailyChartsKeyboard

router = Router()


@router.callback_query(SettingsCallback.filter(F.action == "language"))
async def settings_language_handler(
    callback: CallbackQuery,
    user: User,
) -> None:
    await callback.message.edit_text(
        _("Choose your language:"),
        reply_markup=LanguageKeyboard.make(user.language_code, action="settings"),
    )
    await callback.answer()


@router.callback_query(SettingsCallback.filter(F.action == "max_results"))
async def settings_max_results_handler(
    callback: CallbackQuery,
    callback_data: SettingsCallback,
    user: User,
) -> None:
    if callback_data.value not in MAX_RESULTS_CYCLE:
        await callback.answer()
        return
    prefs, __ = await UserPreferences.get_or_create(user=user)
    prefs.max_results = callback_data.value
    await prefs.save()
    await callback.message.edit_reply_markup(
        reply_markup=SettingsKeyboard.make(
            language_code=user.language_code,
            max_results=prefs.max_results,
            like_buttons=prefs.like_buttons,
        )
    )
    await callback.answer()


@router.callback_query(SettingsCallback.filter(F.action == "like_buttons"))
async def settings_like_buttons_handler(
    callback: CallbackQuery,
    user: User,
) -> None:
    prefs, __ = await UserPreferences.get_or_create(user=user)
    prefs.like_buttons = not prefs.like_buttons
    await prefs.save()
    await callback.message.edit_reply_markup(
        reply_markup=SettingsKeyboard.make(
            language_code=user.language_code,
            max_results=prefs.max_results,
            like_buttons=prefs.like_buttons,
        )
    )
    await callback.answer()


@router.callback_query(SettingsCallback.filter(F.action == "daily_charts"))
async def settings_daily_charts_handler(
    callback: CallbackQuery,
    user: User,
) -> None:
    schedule = await cache.get(daily_charts_cache_key(user.telegram_id))
    await callback.message.edit_text(
        text=_("Daily charts settings"),
        reply_markup=DailyChartsKeyboard.menu(schedule=schedule),
    )
    await callback.answer()


@router.callback_query(SettingsCallback.filter(F.action == "back"))
async def settings_back_handler(
    callback: CallbackQuery,
    user: User,
) -> None:
    prefs, __ = await UserPreferences.get_or_create(user=user)
    await callback.message.edit_text(
        text=_("<b>Settings</b>\n\nWhat would you like to change?"),
        reply_markup=SettingsKeyboard.make(
            language_code=user.language_code,
            max_results=prefs.max_results,
            like_buttons=prefs.like_buttons,
        ),
    )
    await callback.answer()


@router.callback_query(SettingsCallback.filter(F.action == "close"))
async def settings_close_handler(
    callback: CallbackQuery,
) -> None:
    await safe_delete(callback.message)
    await callback.answer()

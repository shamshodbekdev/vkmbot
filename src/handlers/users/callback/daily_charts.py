from contextlib import suppress
from apscheduler.jobstores.base import JobLookupError
from apscheduler.triggers.cron import CronTrigger
from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup
from aiogram.utils.i18n import gettext as _

from core.cache import cache
from core.scheduler import scheduler
from database.models import User
from filters.callback.daily_charts import DailyChartsCallback
from keyboard.inline.daily_charts import DailyChartsKeyboard
from services.daily_charts import daily_charts_cache_key, daily_charts_job_id, send_daily_charts
from utils.constants import DAILY_CHARTS_COUNTRIES, DAILY_CHARTS_HOUR, DAILY_CHARTS_MINUTE

router = Router()

SCHEDULE_TTL: int = 365 * 24 * 3600
_COUNTRY_NAMES = dict(DAILY_CHARTS_COUNTRIES)


async def _edit(callback: CallbackQuery, text: str, reply_markup: InlineKeyboardMarkup) -> None:
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(text=text, reply_markup=reply_markup)


@router.callback_query(DailyChartsCallback.filter())
async def daily_charts_callback_handler(
    callback: CallbackQuery,
    callback_data: DailyChartsCallback,
    user: User,
) -> None:
    user_id = user.telegram_id
    step = callback_data.step

    if step == "menu":
        schedule = await cache.get(daily_charts_cache_key(user_id))
        await _edit(callback, _("Daily charts settings"), DailyChartsKeyboard.menu(schedule=schedule))

    elif step == "country":
        schedule = await cache.get(daily_charts_cache_key(user_id))
        current = schedule.get("country_code", "") if schedule else ""
        await _edit(
            callback,
            _("Select country for daily charts:"),
            DailyChartsKeyboard.country(current=current, country_page=max(callback_data.page, 0)),
        )

    elif step == "set":
        country_code = callback_data.country_code
        if country_code not in _COUNTRY_NAMES:
            await callback.answer()
            return
        chat_id = callback.message.chat.id
        schedule = dict(country_code=country_code, chat_id=chat_id)
        await cache.set(daily_charts_cache_key(user_id), schedule, ttl=SCHEDULE_TTL)
        scheduler.add_job(
            send_daily_charts,
            trigger=CronTrigger(hour=DAILY_CHARTS_HOUR, minute=DAILY_CHARTS_MINUTE),
            id=daily_charts_job_id(user_id),
            replace_existing=True,
            kwargs=dict(chat_id=chat_id, user_id=user_id, country_code=country_code),
        )
        time_str = "%02d:%02d" % (DAILY_CHARTS_HOUR, DAILY_CHARTS_MINUTE)
        await _edit(
            callback,
            _("Daily charts set: %(flag)s at %(time)s") % dict(flag=_COUNTRY_NAMES[country_code], time=time_str),
            DailyChartsKeyboard.menu(schedule=schedule),
        )

    elif step == "cancel":
        with suppress(JobLookupError):
            scheduler.remove_job(daily_charts_job_id(user_id))
        await cache.delete(daily_charts_cache_key(user_id))
        await _edit(callback, _("Daily charts disabled."), DailyChartsKeyboard.menu(schedule=None))

    await callback.answer()

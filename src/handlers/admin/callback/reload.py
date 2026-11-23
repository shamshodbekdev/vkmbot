import asyncio

from aiogram import Router, F
from aiogram.types import CallbackQuery, BufferedInputFile
from filters.common import IsAdmin
from filters.callback.reload import ReloadCallback
from keyboard.inline.reload import ReloadKeyboard
from services.repositories.statistics import StatisticsService
from services.repositories.analytics import AnalyticsService
from services.charts.statistics import StatisticsChartService
from services.charts.analytics import AnalyticsChartService
from services.health import HealthCheckService
from utils.formatters import build_statistics_caption, build_analytics_caption
from utils.helpers.telegram import safe_delete

router = Router()


@router.callback_query(ReloadCallback.filter(F.action == "statistics"), IsAdmin())
async def reload_statistics_callback(callback: CallbackQuery) -> None:
    report = await StatisticsService.get_report()
    caption = build_statistics_caption(report)
    image = await asyncio.to_thread(StatisticsChartService.generate, report)
    await callback.message.answer_photo(
        photo=BufferedInputFile(image.read(), filename="statistics.png"),
        caption=caption,
        reply_markup=ReloadKeyboard.statistics(),
    )
    await safe_delete(callback.message)
    await callback.answer()


@router.callback_query(ReloadCallback.filter(F.action == "analytics"), IsAdmin())
async def reload_analytics_callback(callback: CallbackQuery) -> None:
    report = await AnalyticsService.get_report()
    health = await HealthCheckService.check_health()
    caption = build_analytics_caption(report, health)
    image = await asyncio.to_thread(AnalyticsChartService.generate, report)
    await callback.message.answer_photo(
        photo=BufferedInputFile(image.read(), filename="analytics.png"),
        caption=caption,
        reply_markup=ReloadKeyboard.analytics(),
    )
    await safe_delete(callback.message)
    await callback.answer()

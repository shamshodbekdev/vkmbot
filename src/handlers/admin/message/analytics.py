import asyncio

from aiogram import Router, F
from aiogram.types import Message, BufferedInputFile
from aiogram.utils.i18n import lazy_gettext as __
from filters.common import IsAdmin
from services.repositories.analytics import AnalyticsService
from services.charts.analytics import AnalyticsChartService
from services.health import HealthCheckService
from keyboard.inline.reload import ReloadKeyboard
from utils.formatters import build_analytics_caption

router = Router()


@router.message(F.text == __("Analytics"), IsAdmin())
async def analytics_handler(message: Message) -> None:
    report = await AnalyticsService.get_report()
    health = await HealthCheckService.check_health()
    caption = build_analytics_caption(report, health)
    image = await asyncio.to_thread(AnalyticsChartService.generate, report)
    await message.answer_photo(
        photo=BufferedInputFile(image.read(), filename="analytics.png"),
        caption=caption,
        reply_markup=ReloadKeyboard.analytics(),
    )

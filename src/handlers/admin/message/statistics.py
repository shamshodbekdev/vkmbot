import asyncio

from aiogram import Router, F
from aiogram.types import Message, BufferedInputFile
from aiogram.utils.i18n import lazy_gettext as __
from filters.common import IsAdmin
from services.repositories.statistics import StatisticsService
from services.charts.statistics import StatisticsChartService
from keyboard.inline.reload import ReloadKeyboard
from utils.formatters import build_statistics_caption

router = Router()


@router.message(F.text == __("Statistics"), IsAdmin())
async def statistics_handler(message: Message) -> None:
    report = await StatisticsService.get_report()
    caption = build_statistics_caption(report)
    image = await asyncio.to_thread(StatisticsChartService.generate, report)
    await message.answer_photo(
        photo=BufferedInputFile(image.read(), filename="statistics.png"),
        caption=caption,
        reply_markup=ReloadKeyboard.statistics(),
    )

"""Redis cache for the admin panel's heavy screens (statistics / analytics).

Both screens run dozens of COUNT queries and draw a chart; with millions of users
that is expensive, so the finished caption + PNG are cached for a short time.
"Reload" buttons bypass the cache.
"""
import asyncio
import base64
import logging
from typing import Tuple

from aiogram.utils.i18n import get_i18n

from core.cache import cache
from services.charts.analytics import AnalyticsChartService
from services.charts.statistics import StatisticsChartService
from services.health import HealthCheckService
from services.repositories.analytics import AnalyticsService
from services.repositories.statistics import StatisticsService
from utils.formatters import build_analytics_caption, build_statistics_caption

logger = logging.getLogger(__name__)

PANEL_CACHE_TTL: int = 60


def _key(name: str) -> str:
    try:
        locale = get_i18n().current_locale
    except LookupError:
        locale = "default"
    return "admin:panel:%s:%s" % (name, locale)


async def _cached(name: str, force: bool, build) -> Tuple[str, bytes]:
    key = _key(name)
    if not force:
        try:
            hit = await cache.get(key)
            if hit:
                return hit["caption"], base64.b64decode(hit["image"])
        except Exception as error:
            logger.debug("panel cache read failed: %r", error)
    caption, image = await build()
    try:
        await cache.set(key, dict(caption=caption, image=base64.b64encode(image).decode()), ttl=PANEL_CACHE_TTL)
    except Exception as error:
        logger.debug("panel cache write failed: %r", error)
    return caption, image


async def statistics_panel(force: bool = False) -> Tuple[str, bytes]:
    async def build():
        report = await StatisticsService.get_report()
        image = await asyncio.to_thread(StatisticsChartService.generate, report)
        return build_statistics_caption(report), image.read()
    return await _cached("statistics", force, build)


async def analytics_panel(force: bool = False) -> Tuple[str, bytes]:
    async def build():
        report = await AnalyticsService.get_report()
        health = await HealthCheckService.check_health()
        image = await asyncio.to_thread(AnalyticsChartService.generate, report)
        return build_analytics_caption(report, health), image.read()
    return await _cached("analytics", force, build)

import datetime
from typing import Optional
from database.models import User
from aiogram.enums import ChatType
from utils.constants import ACTIVE_STATUSES
from utils.constants.language import LANGUAGE_GROUPS
from schemas.analytics import (
    GrowthSchema,
    LanguageGrowthSchema,
    AnalyticsPeriodSchema,
    AnalyticsReportSchema,
)

UTC = datetime.timezone.utc


class AnalyticsService:
    @classmethod
    async def _count_since(cls, days_ago: int) -> int:
        return await User.filter(
            chat_type=ChatType.PRIVATE,
            chat_status__in=ACTIVE_STATUSES,
            created_at__gte=datetime.datetime.now(UTC) - datetime.timedelta(days=days_ago),
        ).count()

    @classmethod
    async def _count_between(cls, days_from: int, days_to: int) -> int:
        return await User.filter(
            chat_type=ChatType.PRIVATE,
            chat_status__in=ACTIVE_STATUSES,
            created_at__gte=datetime.datetime.now(UTC) - datetime.timedelta(days=days_from),
            created_at__lt=datetime.datetime.now(UTC) - datetime.timedelta(days=days_to),
        ).count()

    @classmethod
    async def _count_language_since(cls, language_code: Optional[str], days_ago: int) -> int:
        base = User.filter(
            chat_type=ChatType.PRIVATE,
            chat_status__in=ACTIVE_STATUSES,
            created_at__gte=datetime.datetime.now(UTC) - datetime.timedelta(days=days_ago),
        )
        if language_code is None:
            return await base.filter(language_code__isnull=True).count()
        return await base.filter(language_code__in=LANGUAGE_GROUPS.get(language_code, (language_code,))).count()

    @classmethod
    async def _count_language_between(cls, language_code: Optional[str], days_from: int, days_to: int) -> int:
        base = User.filter(
            chat_type=ChatType.PRIVATE,
            chat_status__in=ACTIVE_STATUSES,
            created_at__gte=datetime.datetime.now(UTC) - datetime.timedelta(days=days_from),
            created_at__lt=datetime.datetime.now(UTC) - datetime.timedelta(days=days_to),
        )
        if language_code is None:
            return await base.filter(language_code__isnull=True).count()
        return await base.filter(language_code__in=LANGUAGE_GROUPS.get(language_code, (language_code,))).count()

    @staticmethod
    def _growth_rate(current: int, previous: int) -> float:
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return round((current - previous) / previous * 100, 2)

    @classmethod
    async def _growth(cls, days_current: int, days_from: int, days_to: int) -> GrowthSchema:
        current = await cls._count_since(days_current)
        previous = await cls._count_between(days_from, days_to)
        return GrowthSchema(
            current=current,
            previous=previous,
            change=current - previous,
            rate=cls._growth_rate(current, previous),
        )

    @classmethod
    async def _language_growth(cls, days_current: int, days_from: int, days_to: int) -> LanguageGrowthSchema:
        async def _make(code: Optional[str]) -> GrowthSchema:
            current = await cls._count_language_since(code, days_current)
            previous = await cls._count_language_between(code, days_from, days_to)
            return GrowthSchema(
                current=current,
                previous=previous,
                change=current - previous,
                rate=cls._growth_rate(current, previous),
            )
        return LanguageGrowthSchema(
            uz=await _make("uz"),
            ru=await _make("ru"),
            en=await _make("en"),
            not_set=await _make(None),
        )

    @classmethod
    async def get_report(cls) -> AnalyticsReportSchema:
        return AnalyticsReportSchema(
            daily=AnalyticsPeriodSchema(
                users=await cls._growth(1, 2, 1),
                languages=await cls._language_growth(1, 2, 1),
            ),
            weekly=AnalyticsPeriodSchema(
                users=await cls._growth(7, 14, 7),
                languages=await cls._language_growth(7, 14, 7),
            ),
            monthly=AnalyticsPeriodSchema(
                users=await cls._growth(30, 60, 30),
                languages=await cls._language_growth(30, 60, 30),
            ),
        )

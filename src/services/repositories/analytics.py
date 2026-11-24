import datetime
from typing import Optional
from tortoise import Tortoise

from database.models import User
from aiogram.enums import ChatType
from utils.constants import ACTIVE_STATUSES
from utils.constants.language import LANGUAGE_GROUPS
from schemas.analytics import (
    GrowthSchema,
    LanguageGrowthSchema,
    AnalyticsPeriodSchema,
    AnalyticsReportSchema,
    DailyCountSchema,
)

UTC = datetime.timezone.utc
TREND_DAYS: int = 30
TREND_TIMEZONE: str = "Asia/Tashkent"


def _tz() -> datetime.tzinfo:
    from zoneinfo import ZoneInfo
    return ZoneInfo(TREND_TIMEZONE)


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
    async def _daily_new(cls, days: int = TREND_DAYS) -> list:
        """New private users per Tashkent day for the last ``days`` days (one GROUP BY on the created_at index)."""
        today = datetime.datetime.now(UTC).astimezone(_tz()).date()
        first = today - datetime.timedelta(days=days - 1)
        rows = await Tortoise.get_connection("default").execute_query_dict(
            "SELECT (created_at AT TIME ZONE $1)::date AS day, COUNT(*) AS count FROM users "
            "WHERE chat_type = $2 AND chat_status = ANY($3::varchar[]) AND created_at >= $4 "
            "GROUP BY 1",
            [
                TREND_TIMEZONE,
                ChatType.PRIVATE.value,
                [status.value for status in ACTIVE_STATUSES],
                datetime.datetime.combine(first, datetime.time(), tzinfo=_tz()),
            ],
        )
        counts = {row["day"]: row["count"] for row in rows}
        return [
            DailyCountSchema(day=day, count=counts.get(day, 0))
            for day in (first + datetime.timedelta(days=offset) for offset in range(days))
        ]

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
            daily_new=await cls._daily_new(),
        )

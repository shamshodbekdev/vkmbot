import datetime
from dataclasses import dataclass, field
from typing import List


@dataclass
class GrowthSchema:
    current: int
    previous: int
    change: int
    rate: float


@dataclass
class LanguageGrowthSchema:
    uz: GrowthSchema
    ru: GrowthSchema
    en: GrowthSchema
    not_set: GrowthSchema


@dataclass
class AnalyticsPeriodSchema:
    users: GrowthSchema
    languages: LanguageGrowthSchema


@dataclass
class DailyCountSchema:
    day: datetime.date
    count: int


@dataclass
class AnalyticsReportSchema:
    daily: AnalyticsPeriodSchema
    weekly: AnalyticsPeriodSchema
    monthly: AnalyticsPeriodSchema
    # New private users per day (Tashkent calendar days), oldest first, for the trend chart.
    daily_new: List[DailyCountSchema] = field(default_factory=list)

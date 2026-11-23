from dataclasses import dataclass


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
class AnalyticsReportSchema:
    daily: AnalyticsPeriodSchema
    weekly: AnalyticsPeriodSchema
    monthly: AnalyticsPeriodSchema

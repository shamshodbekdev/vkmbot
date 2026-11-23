from dataclasses import dataclass


@dataclass
class CountSchema:
    count: int


@dataclass
class TotalSchema:
    total: int


@dataclass
class TypesSchema:
    private: CountSchema
    group: CountSchema
    supergroup: CountSchema
    channel: CountSchema


@dataclass
class StatusSchema:
    member: CountSchema
    administrator: CountSchema
    creator: CountSchema
    left: CountSchema
    kicked: CountSchema


@dataclass
class LanguagesSchema:
    uz: CountSchema
    ru: CountSchema
    en: CountSchema
    not_set: CountSchema


@dataclass
class SummarySchema:
    total_count: TotalSchema
    types: TypesSchema
    status: StatusSchema
    premium: CountSchema
    languages: LanguagesSchema


@dataclass
class PeriodSchema:
    new_private: CountSchema
    new_groups: CountSchema
    active_private: CountSchema
    active_groups: CountSchema


@dataclass
class MediaSchema:
    youtube: TotalSchema
    instagram: TotalSchema
    tiktok: TotalSchema


@dataclass
class StatisticsReportSchema:
    summary: SummarySchema
    daily: PeriodSchema
    weekly: PeriodSchema
    monthly: PeriodSchema
    media: MediaSchema

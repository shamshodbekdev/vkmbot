import datetime
from typing import Optional, Sequence
from database.models import User, YoutubeAudio, InstagramMedia, TikTokMedia
from aiogram.enums import ChatType, ChatMemberStatus
from utils.constants import ACTIVE_STATUSES
from utils.constants.language import LANGUAGE_GROUPS
from schemas.statistics import (
    CountSchema,
    TotalSchema,
    TypesSchema,
    StatusSchema,
    LanguagesSchema,
    SummarySchema,
    PeriodSchema,
    MediaSchema,
    StatisticsReportSchema,
)

UTC = datetime.timezone.utc


class StatisticsService:
    @classmethod
    async def _get_total_users(cls) -> int:
        return await User.all().count()

    @classmethod
    async def _get_by_type(cls, types: Sequence[ChatType] = (ChatType.PRIVATE,)) -> int:
        return await User.filter(chat_type__in=types).count()

    @classmethod
    async def _get_by_status(cls, status: Sequence[ChatMemberStatus] = (ChatMemberStatus.MEMBER,)) -> int:
        return await User.filter(chat_status__in=status).count()

    @classmethod
    async def _get_by_created_at(cls, date: datetime.datetime, chat_type: ChatType) -> int:
        if chat_type == ChatType.PRIVATE:
            return await User.filter(
                chat_type=ChatType.PRIVATE,
                created_at__gte=date,
                chat_status__in=ACTIVE_STATUSES,
            ).count()
        return await User.filter(
            chat_type__in=[ChatType.GROUP, ChatType.SUPERGROUP],
            created_at__gte=date,
        ).count()

    @classmethod
    async def _get_by_updated_at(cls, date: datetime.datetime, chat_type: ChatType) -> int:
        if chat_type == ChatType.PRIVATE:
            return await User.filter(
                chat_type=ChatType.PRIVATE,
                updated_at__gte=date,
                chat_status__in=ACTIVE_STATUSES,
            ).count()
        return await User.filter(
            chat_type__in=[ChatType.GROUP, ChatType.SUPERGROUP],
            updated_at__gte=date,
        ).count()

    @classmethod
    async def _get_by_premium(cls, is_premium: bool = True) -> int:
        return await User.filter(is_premium=is_premium).count()

    @classmethod
    async def _get_by_language(cls, language_code: Optional[str] = None) -> int:
        if language_code is None:
            return await User.filter(chat_type=ChatType.PRIVATE, language_code__isnull=True).count()
        return await User.filter(
            chat_type=ChatType.PRIVATE,
            language_code__in=LANGUAGE_GROUPS.get(language_code, (language_code,)),
        ).count()

    @classmethod
    async def get_report(cls) -> StatisticsReportSchema:
        daily = datetime.datetime.now(UTC) - datetime.timedelta(days=1)
        weekly = datetime.datetime.now(UTC) - datetime.timedelta(days=7)
        monthly = datetime.datetime.now(UTC) - datetime.timedelta(days=30)
        return StatisticsReportSchema(
            summary=SummarySchema(
                total_count=TotalSchema(
                    total=await cls._get_total_users(),
                ),
                types=TypesSchema(
                    private=CountSchema(count=await cls._get_by_type([ChatType.PRIVATE])),
                    group=CountSchema(count=await cls._get_by_type([ChatType.GROUP])),
                    supergroup=CountSchema(count=await cls._get_by_type([ChatType.SUPERGROUP])),
                    channel=CountSchema(count=await cls._get_by_type([ChatType.CHANNEL])),
                ),
                status=StatusSchema(
                    member=CountSchema(count=await cls._get_by_status([ChatMemberStatus.MEMBER])),
                    administrator=CountSchema(count=await cls._get_by_status([ChatMemberStatus.ADMINISTRATOR])),
                    creator=CountSchema(count=await cls._get_by_status([ChatMemberStatus.CREATOR])),
                    left=CountSchema(count=await cls._get_by_status([ChatMemberStatus.LEFT])),
                    kicked=CountSchema(count=await cls._get_by_status([ChatMemberStatus.KICKED])),
                ),
                premium=CountSchema(count=await cls._get_by_premium()),
                languages=LanguagesSchema(
                    uz=CountSchema(count=await cls._get_by_language("uz")),
                    ru=CountSchema(count=await cls._get_by_language("ru")),
                    en=CountSchema(count=await cls._get_by_language("en")),
                    not_set=CountSchema(count=await cls._get_by_language()),
                ),
            ),
            daily=PeriodSchema(
                new_private=CountSchema(count=await cls._get_by_created_at(daily, ChatType.PRIVATE)),
                new_groups=CountSchema(count=await cls._get_by_created_at(daily, ChatType.GROUP)),
                active_private=CountSchema(count=await cls._get_by_updated_at(daily, ChatType.PRIVATE)),
                active_groups=CountSchema(count=await cls._get_by_updated_at(daily, ChatType.GROUP)),
            ),
            weekly=PeriodSchema(
                new_private=CountSchema(count=await cls._get_by_created_at(weekly, ChatType.PRIVATE)),
                new_groups=CountSchema(count=await cls._get_by_created_at(weekly, ChatType.GROUP)),
                active_private=CountSchema(count=await cls._get_by_updated_at(weekly, ChatType.PRIVATE)),
                active_groups=CountSchema(count=await cls._get_by_updated_at(weekly, ChatType.GROUP)),
            ),
            monthly=PeriodSchema(
                new_private=CountSchema(count=await cls._get_by_created_at(monthly, ChatType.PRIVATE)),
                new_groups=CountSchema(count=await cls._get_by_created_at(monthly, ChatType.GROUP)),
                active_private=CountSchema(count=await cls._get_by_updated_at(monthly, ChatType.PRIVATE)),
                active_groups=CountSchema(count=await cls._get_by_updated_at(monthly, ChatType.GROUP)),
            ),
            media=MediaSchema(
                youtube=TotalSchema(total=await YoutubeAudio.all().count()),
                instagram=TotalSchema(total=await InstagramMedia.all().count()),
                tiktok=TotalSchema(total=await TikTokMedia.all().count()),
            ),
        )
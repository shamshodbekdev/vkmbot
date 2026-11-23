from contextlib import suppress
import asyncio
import datetime
import logging
from typing import List, Optional

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramForbiddenError,
    TelegramRetryAfter,
    TelegramServerError,
)
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.i18n import gettext as _
from tortoise.queryset import QuerySet

from core.bootstrap import bot as app_bot
from core.cache import cache
from core.i18n import get_i18n
from database.models import User
from database.models.broadcast import BroadcastRecord
from services.broadcast.enums import BroadcastMode
from utils.constants.broadcast import (
    BATCH_DELAY,
    BATCH_SIZE,
    BROADCAST_STATE_TTL,
    MAX_SEND_RETRIES,
    SEND_DELAY,
)

logger = logging.getLogger(__name__)

UTC = datetime.timezone.utc

INACTIVE_STATUSES = (ChatMemberStatus.LEFT, ChatMemberStatus.KICKED)


class BroadcastService:
    """Delivers a message to a filtered audience.

    State lives in Redis under two keys so the job and the admin buttons never
    overwrite each other: ``broadcast:<id>:progress`` is written only by the job,
    ``broadcast:<id>:control`` (paused / stopped) only by the admin handlers.
    """

    @staticmethod
    def _progress_key(broadcast_id: str) -> str:
        return "broadcast:%s:progress" % broadcast_id

    @staticmethod
    def _control_key(broadcast_id: str) -> str:
        return "broadcast:%s:control" % broadcast_id

    @classmethod
    async def init_progress(cls, broadcast_id: str, audience: int) -> None:
        await cache.set(
            cls._progress_key(broadcast_id),
            dict(
                total=0,
                audience=audience,
                success=0,
                failed=0,
                blocked=0,
                started_at=datetime.datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
                finished=False,
            ),
            ttl=BROADCAST_STATE_TTL,
        )
        await cache.set(
            cls._control_key(broadcast_id),
            dict(paused=False, stopped=False),
            ttl=BROADCAST_STATE_TTL,
        )

    @classmethod
    async def _get_control(cls, broadcast_id: str) -> dict:
        control = await cache.get(cls._control_key(broadcast_id))
        return control or dict(paused=False, stopped=False)

    @classmethod
    async def set_paused(cls, broadcast_id: str, paused: bool) -> None:
        control = await cls._get_control(broadcast_id)
        control["paused"] = paused
        await cache.set(cls._control_key(broadcast_id), control, ttl=BROADCAST_STATE_TTL)

    @classmethod
    async def stop(cls, broadcast_id: str) -> None:
        await cache.set(
            cls._control_key(broadcast_id),
            dict(paused=False, stopped=True),
            ttl=BROADCAST_STATE_TTL,
        )

    @classmethod
    async def get_progress(cls, broadcast_id: str) -> Optional[dict]:
        data = await cache.get(cls._progress_key(broadcast_id))
        if not data:
            return None
        control = await cls._get_control(broadcast_id)
        audience = data["audience"]
        percent = min(round(data["total"] * 100 / audience), 100) if audience > 0 else 0
        return dict(
            total=data["total"],
            audience=audience,
            success=data["success"],
            failed=data["failed"],
            blocked=data["blocked"],
            started_at=data["started_at"],
            finished=data["finished"],
            paused=control["paused"],
            stopped=control["stopped"],
            percent=percent,
        )

    @staticmethod
    def _audience(
        languages: Optional[List[str]] = None,
        chat_types: Optional[List[str]] = None,
        is_premium: bool = False,
    ) -> QuerySet[User]:
        query = User.filter(is_blocked=False).exclude(chat_status__in=INACTIVE_STATUSES)
        if languages:
            query = query.filter(language_code__in=languages)
        if chat_types:
            query = query.filter(chat_type__in=chat_types)
        if is_premium:
            query = query.filter(is_premium=True)
        return query

    @classmethod
    async def count_audience(
        cls,
        languages: Optional[List[str]] = None,
        chat_types: Optional[List[str]] = None,
        is_premium: bool = False,
    ) -> int:
        return await cls._audience(languages, chat_types, is_premium).count()

    @classmethod
    async def create(
        cls,
        source_chat_id: int,
        source_message_id: int,
        mode: BroadcastMode,
        broadcast_id: str,
        languages: Optional[List[str]] = None,
        chat_types: Optional[List[str]] = None,
        is_premium: bool = False,
        reply_markup: Optional[dict] = None,
        notify_message_id: Optional[int] = None,
        locale: Optional[str] = None,
    ) -> str:
        """Scheduler job: send the source message to every matching chat."""
        mode = BroadcastMode(mode)
        progress = await cache.get(cls._progress_key(broadcast_id))
        if not progress:
            audience = await cls.count_audience(languages, chat_types, is_premium)
            await cls.init_progress(broadcast_id, audience)
            progress = await cache.get(cls._progress_key(broadcast_id))

        markup = InlineKeyboardMarkup.model_validate(reply_markup) if reply_markup else None
        last_id = None
        stopped = False
        try:
            while not stopped:
                # Keyset pagination: stable even when rows leave the filter mid-run.
                query = cls._audience(languages, chat_types, is_premium).order_by("id")
                if last_id is not None:
                    query = query.filter(id__gt=last_id)
                batch = await query.limit(BATCH_SIZE).values_list("id", "telegram_id")
                if not batch:
                    break

                for row_id, chat_id in batch:
                    last_id = row_id
                    control = await cls._get_control(broadcast_id)
                    while control["paused"] and not control["stopped"]:
                        await asyncio.sleep(1)
                        control = await cls._get_control(broadcast_id)
                    if control["stopped"]:
                        stopped = True
                        break

                    result = await cls._send(
                        bot=app_bot,
                        chat_id=chat_id,
                        source_chat_id=source_chat_id,
                        source_message_id=source_message_id,
                        mode=mode,
                        reply_markup=markup,
                    )
                    progress["total"] += 1
                    progress[result] += 1
                    await cache.set(cls._progress_key(broadcast_id), progress, ttl=BROADCAST_STATE_TTL)
                    await asyncio.sleep(SEND_DELAY)
                await asyncio.sleep(BATCH_DELAY)
        except Exception:
            logger.exception("Broadcast %s crashed", broadcast_id)
        finally:
            progress["finished"] = True
            await cache.set(cls._progress_key(broadcast_id), progress, ttl=BROADCAST_STATE_TTL)
            await BroadcastRecord.create(
                languages=languages or [],
                chat_types=chat_types or [],
                is_premium=is_premium,
                mode=mode.value,
                audience=progress["audience"],
                total=progress["total"],
                success=progress["success"],
                failed=progress["failed"],
                blocked=progress["blocked"],
            )
            logger.info(
                "Broadcast %s finished: total=%s success=%s failed=%s blocked=%s",
                broadcast_id,
                progress["total"],
                progress["success"],
                progress["failed"],
                progress["blocked"],
            )
            await cls._notify_finished(
                admin_chat_id=source_chat_id,
                broadcast_id=broadcast_id,
                notify_message_id=notify_message_id,
                locale=locale,
            )
        return broadcast_id

    @classmethod
    async def _notify_finished(
        cls,
        admin_chat_id: int,
        broadcast_id: str,
        notify_message_id: Optional[int],
        locale: Optional[str],
    ) -> None:
        # Imported lazily: keyboards/formatters import this module's enums.
        from keyboard.inline.broadcast_progress import BroadcastProgressKeyboard
        from utils.formatters import build_broadcast_progress

        progress = await cls.get_progress(broadcast_id)
        if not progress:
            return
        i18n = get_i18n()
        with i18n.context(), i18n.use_locale(locale or i18n.default_locale):
            status = _("Stopped") if progress["stopped"] else _("Completed")
            text = "<b>%s</b>\n\n%s" % (_("Broadcast finished"), build_broadcast_progress(progress, status))
            markup = BroadcastProgressKeyboard.make(broadcast_id=broadcast_id, finished=True)
        try:
            if notify_message_id:
                with suppress(TelegramAPIError):
                    await app_bot.edit_message_reply_markup(
                        chat_id=admin_chat_id,
                        message_id=notify_message_id,
                        reply_markup=markup,
                    )
            await app_bot.send_message(chat_id=admin_chat_id, text=text)
        except TelegramAPIError as error:
            logger.warning("Cannot notify admin about broadcast %s: %s", broadcast_id, error)

    @staticmethod
    async def _send(
        bot: Bot,
        chat_id: int,
        source_chat_id: int,
        source_message_id: int,
        mode: BroadcastMode,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
    ) -> str:
        for _attempt in range(MAX_SEND_RETRIES):
            try:
                if mode == BroadcastMode.FORWARD:
                    await bot.forward_message(
                        chat_id=chat_id,
                        from_chat_id=source_chat_id,
                        message_id=source_message_id,
                    )
                else:
                    await bot.copy_message(
                        chat_id=chat_id,
                        from_chat_id=source_chat_id,
                        message_id=source_message_id,
                        reply_markup=reply_markup,
                    )
                return "success"
            except TelegramRetryAfter as error:
                await asyncio.sleep(error.retry_after + 1)
            except TelegramForbiddenError:
                # The bot was blocked/kicked: mark the chat inactive. This must not
                # touch ``is_blocked``, which is the admin ban flag.
                await User.filter(telegram_id=chat_id).update(chat_status=ChatMemberStatus.KICKED)
                return "blocked"
            except TelegramServerError:
                await asyncio.sleep(5)
            except TelegramAPIError:
                return "failed"
            except Exception:
                logger.exception("Unexpected broadcast error for chat_id=%s", chat_id)
                return "failed"
        return "failed"

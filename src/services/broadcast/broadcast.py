from contextlib import suppress
import asyncio
import datetime
import logging
import time
from collections import deque
from typing import Any, Deque, Dict, List, Optional

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNetworkError,
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
    BATCH_SIZE,
    BROADCAST_STATE_TTL,
    LIVE_UPDATE_INTERVAL,
    MAX_SEND_RETRIES,
    RATE_PER_SECOND,
)

logger = logging.getLogger(__name__)

UTC = datetime.timezone.utc

INACTIVE_STATUSES = (ChatMemberStatus.LEFT, ChatMemberStatus.KICKED)
# Errors meaning the chat can never receive messages from the bot again.
_GONE_CHAT_ERRORS = ("chat not found", "user is deactivated", "bot was kicked", "peer_id_invalid")


class _FloodGate:
    """Shared pause for all concurrent sends after Telegram answers "retry after"."""

    def __init__(self) -> None:
        self._until = 0.0

    def hold(self, seconds: float) -> None:
        self._until = max(self._until, time.monotonic() + seconds)

    async def wait(self) -> None:
        delay = self._until - time.monotonic()
        if delay > 0:
            await asyncio.sleep(delay)


class _RateLimiter:
    """Sliding window: never more than ``rate`` sends in any 1-second window.

    Each send's real timestamp is recorded, so late wake-ups cannot make sends
    bunch up. Retries go through it too.
    """

    def __init__(self, rate: int) -> None:
        self._rate = rate
        self._sent: Deque[float] = deque()
        self._paused_until = 0.0
        self._lock = asyncio.Lock()

    def delay(self, seconds: float) -> None:
        self._paused_until = max(self._paused_until, time.monotonic() + seconds)

    async def acquire(self) -> None:
        async with self._lock:
            while True:
                now = time.monotonic()
                if now < self._paused_until:
                    await asyncio.sleep(self._paused_until - now)
                    continue
                while self._sent and now - self._sent[0] >= 1.0:
                    self._sent.popleft()
                if len(self._sent) < self._rate:
                    self._sent.append(now)
                    return
                await asyncio.sleep(1.0 - (now - self._sent[0]))


def progress_bar(percent: int, width: int = 12) -> str:
    filled = max(0, min(width, round(percent * width / 100)))
    return "▰" * filled + "▱" * (width - filled)


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

    @staticmethod
    def _params_key(broadcast_id: str) -> str:
        return "broadcast:%s:params" % broadcast_id

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
        """Scheduler job: send the source message to every matching chat.

        Runs on the bot's event loop and only awaits I/O, so polling is never blocked.
        Progress (including the last processed user) is saved after every chunk, so a
        broadcast interrupted by a restart is resumed by :meth:`resume_interrupted`.
        """
        mode = BroadcastMode(mode)
        params: Dict[str, Any] = dict(
            source_chat_id=source_chat_id,
            source_message_id=source_message_id,
            mode=mode.value,
            broadcast_id=broadcast_id,
            languages=languages or [],
            chat_types=chat_types or [],
            is_premium=is_premium,
            reply_markup=reply_markup,
            notify_message_id=notify_message_id,
            locale=locale,
        )
        await cache.set(cls._params_key(broadcast_id), params, ttl=BROADCAST_STATE_TTL)

        progress = await cache.get(cls._progress_key(broadcast_id))
        if not progress:
            audience = await cls.count_audience(languages, chat_types, is_premium)
            await cls.init_progress(broadcast_id, audience)
            progress = await cache.get(cls._progress_key(broadcast_id))
        if progress.get("last_id"):
            logger.info("Broadcast %s resumes after %s sent", broadcast_id, progress["total"])

        markup = InlineKeyboardMarkup.model_validate(reply_markup) if reply_markup else None
        gate = _FloodGate()
        limiter = _RateLimiter(RATE_PER_SECOND)
        interrupted = False
        last_live = 0.0
        try:
            stopped = False
            while not stopped:
                # Keyset pagination: stable even when rows leave the filter mid-run.
                query = cls._audience(languages, chat_types, is_premium).order_by("id")
                if progress.get("last_id"):
                    query = query.filter(id__gt=progress["last_id"])
                page = await query.limit(BATCH_SIZE).values_list("id", "telegram_id")
                if not page:
                    break

                for start in range(0, len(page), RATE_PER_SECOND):
                    control = await cls._get_control(broadcast_id)
                    if control["paused"] and not control["stopped"]:
                        await cls._live_update(broadcast_id, source_chat_id, notify_message_id, locale)
                    while control["paused"] and not control["stopped"]:
                        await asyncio.sleep(1)
                        control = await cls._get_control(broadcast_id)
                    if control["stopped"]:
                        stopped = True
                        break

                    chunk = page[start:start + RATE_PER_SECOND]
                    chunk_task = asyncio.ensure_future(asyncio.gather(*(
                        cls._send(
                            bot=app_bot,
                            chat_id=chat_id,
                            source_chat_id=source_chat_id,
                            source_message_id=source_message_id,
                            mode=mode,
                            reply_markup=markup,
                            gate=gate,
                            limiter=limiter,
                        )
                        for _row_id, chat_id in chunk
                    )))
                    try:
                        # Shielded: on shutdown the in-flight chunk is finished and counted,
                        # so a resumed broadcast never sends these messages twice.
                        results = await asyncio.shield(chunk_task)
                    except asyncio.CancelledError:
                        results = await chunk_task
                        cls._count(progress, results, chunk)
                        await cache.set(cls._progress_key(broadcast_id), progress, ttl=BROADCAST_STATE_TTL)
                        raise
                    cls._count(progress, results, chunk)
                    await cache.set(cls._progress_key(broadcast_id), progress, ttl=BROADCAST_STATE_TTL)

                    if time.monotonic() - last_live >= LIVE_UPDATE_INTERVAL:
                        last_live = time.monotonic()
                        await cls._live_update(broadcast_id, source_chat_id, notify_message_id, locale)
        except asyncio.CancelledError:
            # The bot is shutting down: keep the saved progress, resume on next start.
            interrupted = True
            logger.warning("Broadcast %s interrupted at %s/%s", broadcast_id, progress["total"], progress["audience"])
            raise
        except Exception:
            logger.exception("Broadcast %s crashed", broadcast_id)
        finally:
            if not interrupted:
                await cls._finish(broadcast_id, progress, params)
        return broadcast_id

    @staticmethod
    def _count(progress: dict, results: List[str], chunk) -> None:
        for result in results:
            progress["total"] += 1
            progress[result] += 1
        progress["last_id"] = str(chunk[-1][0])

    @classmethod
    async def _finish(cls, broadcast_id: str, progress: dict, params: Dict[str, Any]) -> None:
        progress["finished"] = True
        await cache.set(cls._progress_key(broadcast_id), progress, ttl=BROADCAST_STATE_TTL)
        with suppress(Exception):
            await cache.delete(cls._params_key(broadcast_id))
        await BroadcastRecord.create(
            languages=params["languages"],
            chat_types=params["chat_types"],
            is_premium=params["is_premium"],
            mode=params["mode"],
            audience=progress["audience"],
            total=progress["total"],
            success=progress["success"],
            failed=progress["failed"],
            blocked=progress["blocked"],
        )
        logger.info(
            "Broadcast %s finished: total=%s success=%s failed=%s blocked=%s",
            broadcast_id, progress["total"], progress["success"], progress["failed"], progress["blocked"],
        )
        await cls._live_update(broadcast_id, params["source_chat_id"], params["notify_message_id"], params["locale"])
        await cls._notify_finished(
            admin_chat_id=params["source_chat_id"],
            broadcast_id=broadcast_id,
            notify_message_id=params["notify_message_id"],
            locale=params["locale"],
        )

    @classmethod
    async def resume_interrupted(cls, scheduler) -> int:
        """Re-schedule broadcasts that were running when the bot stopped. Returns how many."""
        resumed = 0
        pattern = cache.build_key("broadcast:*:params")
        prefix_len = len(cache.build_key(""))
        async for raw_key in cache.client.scan_iter(match=pattern, count=500):
            key = raw_key.decode() if isinstance(raw_key, bytes) else raw_key
            broadcast_id = key[prefix_len:].split(":")[1]
            if scheduler.get_job("broadcast:%s" % broadcast_id):
                continue  # still scheduled (e.g. delayed) or already queued
            progress = await cache.get(cls._progress_key(broadcast_id))
            params = await cache.get(cls._params_key(broadcast_id))
            if not progress or not params or progress.get("finished"):
                continue
            scheduler.add_job(
                cls.create,
                "date",
                id="broadcast:%s" % broadcast_id,
                run_date=datetime.datetime.now(UTC),
                misfire_grace_time=None,
                replace_existing=True,
                kwargs=params,
            )
            resumed += 1
            logger.info("Resuming broadcast %s (%s/%s sent)", broadcast_id, progress["total"], progress["audience"])
        return resumed

    @classmethod
    def render_progress(cls, progress: dict) -> str:
        """Live progress text (call inside an i18n locale context)."""
        from utils.formatters import build_broadcast_progress

        status = (
            _("Completed") if progress["finished"]
            else _("Stopped") if progress["stopped"]
            else _("Paused") if progress["paused"]
            else _("In progress")
        )
        return "<b>%s</b>\n\n<code>%s</code> %s%%\n\n%s" % (
            _("Broadcast"), progress_bar(progress["percent"]), progress["percent"],
            build_broadcast_progress(progress, status),
        )

    @classmethod
    async def _live_update(
        cls, broadcast_id: str, admin_chat_id: int, notify_message_id: Optional[int], locale: Optional[str],
    ) -> None:
        """Edit the admin's progress message with the current numbers."""
        if not notify_message_id:
            return
        from keyboard.inline.broadcast_progress import BroadcastProgressKeyboard

        progress = await cls.get_progress(broadcast_id)
        if not progress:
            return
        i18n = get_i18n()
        with i18n.context(), i18n.use_locale(locale or i18n.default_locale):
            text = cls.render_progress(progress)
            markup = BroadcastProgressKeyboard.make(
                broadcast_id=broadcast_id, paused=progress["paused"], finished=progress["finished"],
            )
        with suppress(TelegramAPIError):
            await app_bot.edit_message_text(
                chat_id=admin_chat_id, message_id=notify_message_id, text=text, reply_markup=markup,
            )

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
        gate: Optional[_FloodGate] = None,
        limiter: Optional[_RateLimiter] = None,
    ) -> str:
        """Deliver to one chat. Returns "success", "blocked" or "failed"; never raises."""
        gate = gate or _FloodGate()
        for attempt in range(MAX_SEND_RETRIES):
            await gate.wait()
            if limiter is not None:
                await limiter.acquire()
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
                # Flood limit: pause every concurrent send, then retry this one.
                logger.warning("Broadcast flood limit: waiting %ss", error.retry_after)
                gate.hold(error.retry_after + 1)
                if limiter is not None:
                    limiter.delay(error.retry_after + 1)
            except TelegramForbiddenError:
                # The bot was blocked/kicked: mark the chat inactive. This must not
                # touch ``is_blocked``, which is the admin ban flag.
                await User.filter(telegram_id=chat_id).update(chat_status=ChatMemberStatus.KICKED)
                return "blocked"
            except TelegramBadRequest as error:
                if any(reason in str(error).lower() for reason in _GONE_CHAT_ERRORS):
                    await User.filter(telegram_id=chat_id).update(chat_status=ChatMemberStatus.KICKED)
                    return "blocked"
                logger.info("Broadcast to %s failed: %s", chat_id, error)
                return "failed"
            except (TelegramServerError, TelegramNetworkError) as error:
                logger.info("Broadcast to %s: temporary error (attempt %d): %s", chat_id, attempt + 1, error)
                await asyncio.sleep(2 * (attempt + 1))
            except TelegramAPIError as error:
                logger.info("Broadcast to %s failed: %s", chat_id, error)
                return "failed"
            except Exception:
                logger.exception("Unexpected broadcast error for chat_id=%s", chat_id)
                return "failed"
        return "failed"

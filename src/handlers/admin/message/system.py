import asyncio
import datetime
import os
import re
import shutil
import time
from contextlib import suppress
from html import escape

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, ReplyKeyboardRemove
from aiogram.utils.i18n import gettext as _, lazy_gettext as __

from core.cache import cache
from core.scheduler import scheduler
from database.models import User
from filters.callback.reload import ReloadCallback
from filters.common import IsModerator, IsSuperAdmin
from keyboard.reply import ManageKeyboard
from services import media_downloader

router = Router()

_STARTED_AT = time.time()
LOG_LINES: int = 50
SERVICE_NAME: str = "vkm-bot"
_TOKEN_PATTERN = re.compile(r"\d{8,10}:[A-Za-z0-9_-]{30,}")
# Labels used before the emoji were removed: admin keyboards already on phones keep
# showing them until /manage is sent again, so they must keep working.
_LEGACY_SYSTEM = {"🩺 Tizim", "🩺 Тизим", "🩺 Система", "🩺 System"}
_LEGACY_LOGS = {"📜 Loglar", "📜 Логлар", "📜 Логи", "📜 Logs"}


def _ok(flag: bool) -> str:
    return "✅" if flag else "❌"


async def _timed(coro) -> tuple:
    started = time.perf_counter()
    try:
        await coro
        return True, (time.perf_counter() - started) * 1000
    except Exception:
        return False, 0.0


def _memory_mb() -> float:
    with suppress(Exception):
        with open("/proc/self/status") as status:
            for line in status:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024
    return 0.0


def _uptime() -> str:
    seconds = int(time.time() - _STARTED_AT)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes = seconds // 60
    return ("%dd %dh %dm" % (days, hours, minutes)) if days else ("%dh %dm" % (hours, minutes))


async def build_system_report(bot: Bot) -> str:
    import yt_dlp

    db_ok, db_ms = await _timed(User.all().limit(1).values_list("id", flat=True))
    redis_ok, redis_ms = await _timed(cache.client.ping())
    tg_ok, tg_ms = await _timed(bot.get_me())
    jobs = -1
    if scheduler.running:
        with suppress(Exception):
            jobs = len(await asyncio.to_thread(scheduler.get_jobs))
    disk = shutil.disk_usage("/")
    load = media_downloader.load_status()
    return _(
        "<b>🩺 System status</b>\n"
        "\n"
        "%(db)s Database  —  <b>%(db_ms).0f ms</b>\n"
        "%(redis)s Redis  —  <b>%(redis_ms).0f ms</b>\n"
        "%(tg)s Telegram API  —  <b>%(tg_ms).0f ms</b>\n"
        "%(sched)s Scheduler  —  <b>%(jobs)s</b> jobs\n"
        "%(ffmpeg)s ffmpeg\n"
        "\n"
        "⬇️ Active downloads  —  <b>%(downloads)s</b> / %(limit)s  (⏳ %(queued)s)\n"
        "🧠 Bot memory  —  <b>%(memory).0f MB</b>\n"
        "💾 Free disk  —  <b>%(disk_free).1f GB</b> / %(disk_total).0f GB\n"
        "⏱ Uptime  —  <b>%(uptime)s</b>\n"
        "📦 yt-dlp  —  <b>%(ytdlp)s</b>\n"
        "\n"
        "<i>%(time)s</i>"
    ) % dict(
        db=_ok(db_ok), db_ms=db_ms,
        redis=_ok(redis_ok), redis_ms=redis_ms,
        tg=_ok(tg_ok), tg_ms=tg_ms,
        sched=_ok(scheduler.running and jobs >= 0), jobs=max(jobs, 0),
        ffmpeg=_ok(shutil.which("ffmpeg") is not None),
        downloads=load["running"], limit=media_downloader.MAX_PARALLEL_DOWNLOADS, queued=load["queued"],
        memory=_memory_mb(),
        disk_free=disk.free / 1024 ** 3, disk_total=disk.total / 1024 ** 3,
        uptime=_uptime(),
        ytdlp=yt_dlp.version.__version__,
        time=datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
    )


def _refresh_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=_("🔄 Refresh"), callback_data=ReloadCallback(action="system").pack()),
    ]])


@router.message(F.text == __("🩺 System"), IsModerator())
@router.message(F.text.in_(_LEGACY_SYSTEM), IsModerator())
async def system_handler(message: Message, bot: Bot) -> None:
    await message.answer(text=await build_system_report(bot), reply_markup=_refresh_keyboard())


@router.callback_query(ReloadCallback.filter(F.action == "system"), IsModerator())
async def system_refresh_callback(callback: CallbackQuery, bot: Bot) -> None:
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(text=await build_system_report(bot), reply_markup=_refresh_keyboard())
    await callback.answer(_("Updated"))


async def read_logs(lines: int = LOG_LINES) -> str:
    process = await asyncio.create_subprocess_exec(
        "journalctl", "-u", SERVICE_NAME, "-n", str(lines), "--no-pager", "-o", "short-iso",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
    )
    try:
        stdout, _stderr = await asyncio.wait_for(process.communicate(), timeout=15)
    except asyncio.TimeoutError:
        process.kill()
        return "journalctl timed out"
    text = stdout.decode(errors="replace").strip() or "(empty)"
    # Defence in depth: never show anything that looks like a bot token.
    return _TOKEN_PATTERN.sub("<token hidden>", text)


@router.message(F.text == __("📜 Logs"), IsSuperAdmin())
@router.message(F.text.in_(_LEGACY_LOGS), IsSuperAdmin())
async def logs_handler(message: Message) -> None:
    logs = await read_logs()
    title = _("📜 Last %(lines)s log lines of %(service)s") % dict(lines=LOG_LINES, service=SERVICE_NAME)
    body = "<b>%s</b>\n\n<pre>%s</pre>" % (escape(title), escape(logs))
    if len(body) <= 4000:
        await message.answer(text=body)
    else:
        await message.answer_document(
            document=BufferedInputFile(logs.encode(), filename="%s-%s.log" % (SERVICE_NAME, datetime.date.today())),
            caption="<b>%s</b>" % escape(title),
        )


@router.message(F.text == __("✖️ Close panel"), IsModerator())
async def close_panel_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(text=_("Admin panel closed. Send /manage to open it again."), reply_markup=ReplyKeyboardRemove())


@router.message(Command("cancel"), StateFilter("*"), IsModerator())
async def cancel_handler(message: Message, state: FSMContext) -> None:
    """Leave any admin step (broadcast setup, user search, ...) and go back to the main menu."""
    had_state = await state.get_state() is not None
    await state.clear()
    await message.answer(
        text=_("❌ Cancelled. Main menu:") if had_state else _("Main menu"),
        reply_markup=ManageKeyboard.make(),
    )

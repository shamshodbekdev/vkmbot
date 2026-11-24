"""/round: turn a video into a Telegram video note (round video).

* ``/round`` as a reply to a video converts that video at once;
* a round video (video note) is turned back into a normal rectangular video;
* ``/round`` alone shows a guide and converts the next video the user sends
  within WAIT_SECONDS; after that the request is cancelled.
"""
import asyncio
import logging
import time
from contextlib import suppress
from typing import Dict, Optional, Tuple

from aiogram import Bot, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.utils.i18n import gettext as _

from middlewares.download_limit import DownloadLimitMiddleware
from services.media_downloader import as_input_file, discard_dir
from services.video_note import MAX_SECONDS, make_regular_video, make_video_note
from states import RoundState
from utils.constants import MAX_FILE_SIZE, MAX_FILE_SIZE_MB
from utils.helpers import safe_delete

router = Router()
# Converting holds one of the user's download slots, like any other download.
router.message.middleware(DownloadLimitMiddleware())
logger = logging.getLogger(__name__)

VIDEO_NOTE_UPLOAD_TIMEOUT: int = 300
WAIT_SECONDS: int = 60
# One pending "no video came" timer per (chat, user); a new /round or a video cancels it.
_timers: Dict[Tuple[int, int], asyncio.Task] = {}


def _cancel_timer(key: Tuple[int, int]) -> None:
    task = _timers.pop(key, None)
    if task is not None and task is not asyncio.current_task():
        task.cancel()


def _key(message: Message) -> Tuple[int, int]:
    return message.chat.id, message.from_user.id if message.from_user else 0


def _timeout_text() -> str:
    return _("⌛️ No video arrived within %(seconds)s seconds. /round was cancelled.") % dict(seconds=WAIT_SECONDS)


async def _expire(message: Message, state: FSMContext, started: float, text: str) -> None:
    """After WAIT_SECONDS: if this /round is still waiting, cancel it and say so."""
    key = _key(message)
    try:
        await asyncio.sleep(WAIT_SECONDS)
        data = await state.get_data()
        if await state.get_state() == RoundState.WAITING_VIDEO.state and data.get("round_started") == started:
            await state.clear()
            with suppress(Exception):
                await message.answer(text=text)
    except asyncio.CancelledError:
        pass
    except Exception:
        logger.exception("/round timeout failed")
    finally:
        if _timers.get(key) is asyncio.current_task():
            _timers.pop(key, None)


def video_of(message: Optional[Message]) -> Optional[Tuple[str, int, bool]]:
    """(file_id, size, is_round) of the video in ``message``: a video, GIF, round video or video file."""
    if message is None:
        return None
    if message.video_note is not None:
        return message.video_note.file_id, message.video_note.file_size or 0, True
    media = message.video or message.animation
    if media is None and message.document and (message.document.mime_type or "").startswith("video/"):
        media = message.document
    if media is None:
        return None
    return media.file_id, media.file_size or 0, False


def _is_video(message: Message) -> bool:
    return video_of(message) is not None


async def _to_rectangular(message: Message, bot: Bot, file_id: str) -> None:
    """Round video -> normal (rectangular) MP4 video."""
    processing = await message.answer(text=_("Converting the round video to a rectangular one..."))
    video = None
    try:
        video = await make_regular_video(bot, file_id)
        if video is None:
            await message.answer(text=_("❌ Could not convert this video. Please send another one."))
            return
        await message.answer_video(
            video=as_input_file(str(video.path), timeout=VIDEO_NOTE_UPLOAD_TIMEOUT),
            width=video.width or None,
            height=video.height or None,
            duration=video.duration or None,
            supports_streaming=True,
            caption=_("✅ The video was sent in rectangular format."),
        )
    except Exception:
        logger.exception("Sending the rectangular video failed")
        await message.answer(text=_("❌ Could not convert this video. Please send another one."))
    finally:
        await safe_delete(processing)
        if video is not None:
            discard_dir(video.job_dir)


async def _convert(message: Message, bot: Bot, file_id: str, size: int, is_round: bool = False) -> None:
    if size > MAX_FILE_SIZE:
        await message.answer(text=_("File is too large. Maximum size is %(limit)sMB.") % dict(limit=MAX_FILE_SIZE_MB))
        return
    if is_round:
        await _to_rectangular(message, bot, file_id)
        return
    processing = await message.answer(text=_("Processing..."))
    note = None
    try:
        note = await make_video_note(bot, file_id)
        if note is None:
            await message.answer(text=_("❌ Could not convert this video. Please send another one."))
            return
        await message.answer_video_note(
            video_note=as_input_file(str(note.path), timeout=VIDEO_NOTE_UPLOAD_TIMEOUT),
            length=note.length,
            duration=note.duration,
        )
        if note.truncated:
            await message.answer(
                text=_("✂️ The video was longer than %(seconds)s seconds, so only the first %(seconds)s seconds were used.")
                % dict(seconds=MAX_SECONDS)
            )
    except Exception:
        logger.exception("Sending the video note failed")
        await message.answer(text=_("❌ Could not convert this video. Please send another one."))
    finally:
        await safe_delete(processing)
        if note is not None:
            discard_dir(note.job_dir)


@router.message(Command("round"))
async def round_command_handler(message: Message, bot: Bot, state: FSMContext) -> None:
    key = _key(message)
    _cancel_timer(key)
    replied = video_of(message.reply_to_message)
    if replied is not None:
        await state.clear()
        await _convert(message, bot, *replied)
        return
    started = time.time()
    await state.set_state(RoundState.WAITING_VIDEO)
    await state.update_data(round_started=started)
    await message.answer(text=_(
        "🎥 /round — turn a video into a round video (Telegram Video Note)\n\n"
        "How does it work?\n\n"
        "1) Convert a new video\n"
        "• First type /round\n"
        "• Then send the video\n"
        "✅ The bot turns the video into a round one and sends it back.\n\n"
        "2) Convert a video already in the chat\n"
        "• Reply to any video in the chat with the bot\n"
        "• Type /round in the reply\n"
        "✅ The bot turns that video into a round one and sends it back.\n\n"
        "Note:\n"
        "• Works only with video files.\n"
        "• Very large or very long videos may be cut or rejected.\n\n"
        "⏳ Now send the video you want to make round:"
    ))
    # The text is resolved now: the timer runs outside this update's language context.
    _timers[key] = asyncio.create_task(_expire(message, state, started, _timeout_text()))


@router.message(StateFilter(RoundState.WAITING_VIDEO), F.func(_is_video))
async def round_video_handler(message: Message, bot: Bot, state: FSMContext) -> None:
    _cancel_timer(_key(message))
    started = (await state.get_data()).get("round_started") or 0
    await state.clear()
    if time.time() - started > WAIT_SECONDS:
        # The wait ran out while the bot was restarting (its timer was lost).
        await message.answer(text=_timeout_text())
        return
    await _convert(message, bot, *video_of(message))

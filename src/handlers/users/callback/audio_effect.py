import logging
from pathlib import Path
from typing import Optional

import aiofiles
from aiogram import Bot, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery
from aiogram.utils.i18n import gettext as _

from core.cache import cache
from core.config import config
from filters.callback import AudioEffectCallback
from services.audio_effects import EFFECTS, apply_effect
from services.media_downloader import as_input_file, discard, new_job_dir
from services.youtube_api import YouTubeAPI
from utils.helpers import download_file_bytes, safe_delete

router = Router()
logger = logging.getLogger(__name__)

EFFECT_CACHE_TTL: int = 30 * 24 * 60 * 60
# getFile on api.telegram.org only serves files up to 20 MB.
BOT_API_DOWNLOAD_LIMIT: int = 20 * 1024 * 1024


def _cache_key(effect: str, video_id: str) -> str:
    return "fx:%s:%s" % (effect, video_id)


def _caption() -> str:
    return _("Find any music you want quickly and easily via %(username_bot)s!") % dict(
        username_bot=config.telegram_username,
    )


async def _source_file(bot: Bot, callback: CallbackQuery, video_id: str) -> Optional[Path]:
    """The original track: from the message the button is on, else downloaded again."""
    audio = callback.message.audio if callback.message else None
    small_enough = audio is not None and (config.telegram_api_local or (audio.file_size or 0) <= BOT_API_DOWNLOAD_LIMIT)
    if small_enough:
        try:
            data = await download_file_bytes(bot, audio.file_id)
            path = new_job_dir() / ("source%s" % (Path(audio.file_name or "a.m4a").suffix or ".m4a"))
            async with aiofiles.open(path, "wb") as file:
                await file.write(data)
            return path
        except Exception as error:
            logger.info("Cannot download audio %s from Telegram (%r), fetching it again", video_id, error)
    downloaded = await YouTubeAPI.download_audio(video_id)
    return downloaded.path if downloaded else None


@router.callback_query(AudioEffectCallback.filter())
async def audio_effect_callback_handler(callback: CallbackQuery, callback_data: AudioEffectCallback, bot: Bot) -> None:
    effect = EFFECTS.get(callback_data.effect)
    if effect is None or callback.message is None:
        await callback.answer()
        return

    audio = callback.message.audio
    title = (audio.title if audio and audio.title else "") or "Audio"
    performer = audio.performer if audio else None
    effect_title = "%s (%s)" % (title, effect.suffix)

    cached_file_id = None
    try:
        cached_file_id = await cache.get(_cache_key(effect.key, callback_data.video_id))
    except Exception as error:
        logger.debug("Effect cache read failed: %r", error)
    if cached_file_id:
        await callback.answer()
        try:
            await callback.message.answer_audio(audio=cached_file_id, title=effect_title, performer=performer, caption=_caption())
            return
        except TelegramBadRequest:
            logger.info("Cached effect file_id expired for %s", callback_data.video_id)

    await callback.answer(_("Applying the effect..."))
    processing = await callback.message.answer(text=_("Processing..."))
    source: Optional[Path] = None
    result: Optional[Path] = None
    try:
        source = await _source_file(bot, callback, callback_data.video_id)
        result = await apply_effect(source, effect.key) if source else None
        if not result:
            await callback.message.answer(text=_("Could not apply the effect."))
            return
        sent = await callback.message.answer_audio(
            audio=as_input_file(str(result), filename="%s.mp3" % effect_title[:120]),
            title=effect_title[:64],
            performer=performer,
            caption=_caption(),
        )
        if sent.audio:
            try:
                await cache.set(_cache_key(effect.key, callback_data.video_id), sent.audio.file_id, ttl=EFFECT_CACHE_TTL)
            except Exception as error:
                logger.debug("Effect cache write failed: %r", error)
    except Exception:
        logger.exception("Audio effect %s failed for %s", effect.key, callback_data.video_id)
        await callback.message.answer(text=_("Could not apply the effect."))
    finally:
        discard(str(source) if source else None, str(result) if result else None)
        await safe_delete(processing)

import logging
import os
from io import BytesIO
from typing import Optional

import aiofiles
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InaccessibleMessage, MaybeInaccessibleMessageUnion

logger = logging.getLogger(__name__)


async def safe_delete(message: Optional[MaybeInaccessibleMessageUnion]) -> bool:
    """Delete a message, ignoring the usual "too old / already deleted" errors."""
    if message is None or isinstance(message, InaccessibleMessage):
        return False
    try:
        return await message.delete()
    except TelegramBadRequest as error:
        logger.debug("Cannot delete message %s: %s", message.message_id, error)
        return False


async def download_audio_sample(bot: Bot, file_id: str, seconds: int) -> Optional[bytes]:
    """First ``seconds`` of a Telegram audio/video file as 16 kHz mono WAV.

    With a local Bot API server ffmpeg reads the stored file directly (only the
    needed part, whatever the file size) and the file is removed afterwards.
    On api.telegram.org the (at most 20 MB) file is downloaded as before.
    """
    from services.shazam_api import to_wav, wav_from_path

    file = await bot.get_file(file_id)
    path = file.file_path or ""
    if os.path.isabs(path) and os.path.exists(path):
        try:
            return await wav_from_path(path, seconds)
        finally:
            try:
                os.remove(path)
            except OSError:
                logger.warning("Cannot remove downloaded file %s", path)
    buffer = BytesIO()
    await bot.download_file(path, destination=buffer)
    return await to_wav(buffer.getvalue(), seconds)


async def download_file_bytes(bot: Bot, file_id: str) -> bytes:
    """Download a Telegram file into memory.

    Works with both the official Bot API and a local Bot API server: in ``--local``
    mode ``getFile`` returns an absolute path on this machine, which is read and
    removed directly instead of going through HTTP.
    """
    file = await bot.get_file(file_id)
    path = file.file_path or ""
    if os.path.isabs(path) and os.path.exists(path):
        try:
            async with aiofiles.open(path, "rb") as source:
                return await source.read()
        finally:
            try:
                os.remove(path)
            except OSError:
                logger.warning("Cannot remove downloaded file %s", path)

    buffer = BytesIO()
    await bot.download_file(path, destination=buffer)
    return buffer.getvalue()

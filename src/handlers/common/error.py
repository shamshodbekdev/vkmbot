from contextlib import suppress
import logging

from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import ErrorEvent

router = Router()
logger = logging.getLogger(__name__)


@router.error()
async def error_handler(event: ErrorEvent) -> None:
    logger.exception(
        "Unhandled error while processing update %s: %s",
        event.update.update_id,
        event.exception,
        exc_info=event.exception,
    )
    callback = event.update.callback_query
    if callback is not None:
        with suppress(TelegramAPIError):
            await callback.answer()

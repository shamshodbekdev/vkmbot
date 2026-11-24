import asyncio
import logging
import os

from aiogram import Bot

from core.bootstrap import bot, dp
from core.bot_identity import load_bot_username
from core.cache import cache
from core.commands import Commands
from core.i18n import get_i18n
from core.scheduler import scheduler
from services.media_downloader import close_http_session, configure_executors, shutdown_executors
from database.connect import Database
from handlers import router
from services.broadcast.broadcast import BroadcastService
from middlewares import (
    BlockedMiddleware,
    I18nMiddleware,
    RegisterMiddleware,
    SubscriptionMiddleware,
    ThrottlerMiddleware,
)

logger = logging.getLogger(__name__)


def setup_middlewares() -> None:
    # Order matters: the user is loaded first, then the locale is resolved from it,
    # so every following middleware and handler can reply in the user's language.
    dp.update.middleware.register(RegisterMiddleware())
    dp.update.middleware.register(I18nMiddleware(i18n=get_i18n()))
    dp.update.middleware.register(ThrottlerMiddleware())
    dp.update.middleware.register(BlockedMiddleware())
    dp.update.middleware.register(SubscriptionMiddleware())


async def on_startup(bot: Bot) -> None:
    logger.info("Application is starting up...")
    configure_executors()
    await Database.connect()
    await load_bot_username(bot)
    await Commands.set_commands(bot)
    scheduler.start()
    resumed = await BroadcastService.resume_interrupted(scheduler)
    if resumed:
        logger.info("Resumed %d interrupted broadcast(s)", resumed)
    logger.info("Application started")


async def on_shutdown() -> None:
    logger.info("Application is shutting down...")
    if scheduler.running:
        scheduler.shutdown(wait=False)
    await Database.disconnect()
    shutdown_executors()
    await close_http_session()
    await cache.close()
    await dp.storage.close()


async def main() -> None:
    # Routers and middlewares must be registered before polling starts:
    # start_polling() resolves allowed_updates from the registered handlers.
    setup_middlewares()
    dp.include_router(router)
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    await dp.start_polling(bot)


class _SkipUnhandled(logging.Filter):
    """With privacy mode off the bot receives every group message; most are ignored
    on purpose, so do not write a log line for each of them."""

    def filter(self, record: logging.LogRecord) -> bool:
        return "is not handled" not in record.getMessage()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger("aiogram.event").addFilter(_SkipUnhandled())
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
    # Everything is closed by now (on_shutdown). A download still running in a
    # worker thread would keep Python alive until it finishes (minutes for a big
    # file, so systemd had to SIGKILL the bot): exit without waiting for it.
    logging.shutdown()
    os._exit(0)

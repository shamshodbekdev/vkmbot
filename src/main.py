import asyncio
import logging

from aiogram import Bot

from core.bootstrap import bot, dp
from core.cache import cache
from core.commands import Commands
from core.i18n import get_i18n
from core.scheduler import scheduler
from database.connect import Database
from handlers import router
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
    await Database.connect()
    await Commands.set_commands(bot)
    scheduler.start()
    logger.info("Application started")


async def on_shutdown() -> None:
    logger.info("Application is shutting down...")
    if scheduler.running:
        scheduler.shutdown(wait=False)
    await Database.disconnect()
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


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")

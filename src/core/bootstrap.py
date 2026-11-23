from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.enums.parse_mode import ParseMode
from aiogram.fsm.storage.redis import RedisStorage

from core.config import config

session = AiohttpSession(
    api=TelegramAPIServer.from_base(
        config.telegram_api_url,
        is_local=config.telegram_api_local,
    )
)
bot = Bot(
    session=session,
    token=config.telegram_token.get_secret_value(),
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
storage = RedisStorage.from_url(config.redis_url)
dp = Dispatcher(storage=storage)

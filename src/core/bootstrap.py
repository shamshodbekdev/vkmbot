from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.enums.parse_mode import ParseMode
from aiogram.fsm.storage.redis import RedisStorage

from core.config import config

# With a local Bot API server, sendVideo returns only after the server has uploaded
# the file (up to 2 GB) to Telegram, which can take minutes: allow 30 minutes.
# On api.telegram.org files are at most 50 MB, so aiogram's 60 s default is kept.
REQUEST_TIMEOUT: int = 1800 if config.telegram_api_local else 60

session = AiohttpSession(
    api=TelegramAPIServer.from_base(
        config.telegram_api_url,
        is_local=config.telegram_api_local,
    ),
    timeout=REQUEST_TIMEOUT,
)
bot = Bot(
    session=session,
    token=config.telegram_token.get_secret_value(),
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
storage = RedisStorage.from_url(config.redis_url)
dp = Dispatcher(storage=storage)

"""The bot's real @username, read from Telegram once at startup.

Used for links such as "add to group" (t.me/<bot>?startgroup), which must point
at this bot even if TELEGRAM_USERNAME in .env is set to something else.
"""
import logging

from aiogram import Bot

from core.config import config

logger = logging.getLogger(__name__)

_username: str = config.telegram_username.lstrip("@")


async def load_bot_username(bot: Bot) -> None:
    global _username
    try:
        me = await bot.me()
        if me.username:
            _username = me.username
    except Exception as error:
        logger.warning("Could not read the bot username from Telegram: %r", error)


def bot_username() -> str:
    return _username


def add_to_group_url() -> str:
    return "https://t.me/%s?startgroup=true" % bot_username()

import logging
from typing import List

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault

from core.config import config
from database.enums import UserRole
from database.models import User

logger = logging.getLogger(__name__)


class Commands:
    @staticmethod
    def _user_commands() -> List[BotCommand]:
        return [
            BotCommand(command="my", description="List your playlist"),
            BotCommand(command="top", description="TOP popular tracks"),
            BotCommand(command="mood", description="Get a playlist based on your mood"),
            BotCommand(command="lang", description="Change language"),
            BotCommand(command="settings", description="Others settings"),
        ]

    @classmethod
    def _admin_commands(cls) -> List[BotCommand]:
        return cls._user_commands() + [
            BotCommand(command="manage", description="Manage the bot"),
        ]

    @classmethod
    async def set_admin_commands(cls, bot: Bot, chat_id: int) -> None:
        try:
            await bot.set_my_commands(
                commands=cls._admin_commands(),
                scope=BotCommandScopeChat(chat_id=chat_id),
            )
        except TelegramAPIError as error:
            logger.warning("Failed to set admin commands for %s: %s", chat_id, error)

    @classmethod
    async def remove_admin_commands(cls, bot: Bot, chat_id: int) -> None:
        try:
            await bot.delete_my_commands(scope=BotCommandScopeChat(chat_id=chat_id))
        except TelegramAPIError as error:
            logger.warning("Failed to remove admin commands for %s: %s", chat_id, error)

    @classmethod
    async def set_commands(cls, bot: Bot) -> None:
        await bot.set_my_commands(
            commands=cls._user_commands(),
            scope=BotCommandScopeDefault(),
        )
        admin_ids = set(
            await User.filter(role=UserRole.ADMINISTRATOR).values_list("telegram_id", flat=True)
        )
        admin_ids.add(config.telegram_id)
        for chat_id in admin_ids:
            await cls.set_admin_commands(bot, chat_id)

import logging

from tortoise import Tortoise

from core.config import config

logger = logging.getLogger(__name__)


class Database:
    @staticmethod
    async def connect() -> None:
        await Tortoise.init(
            db_url=config.database_url,
            modules=dict(models=["database.models"]),
        )
        # safe=True only creates missing tables; existing tables are never altered.
        await Tortoise.generate_schemas(safe=True)
        logger.info("Database connected")

    @staticmethod
    async def disconnect() -> None:
        await Tortoise.close_connections()

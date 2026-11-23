import asyncio

from schemas.health import HealthSchema
from core.scheduler import scheduler
from core.cache import cache
from core.bootstrap import bot
from tortoise import Tortoise


class HealthCheckService:
    @classmethod
    async def _check_database(cls) -> bool:
        try:
            await Tortoise.get_connection("default").execute_query("SELECT 1")
            return True
        except Exception:
            return False

    @classmethod
    async def _check_queue(cls) -> bool:
        """The scheduler must be running and its Redis job store reachable."""
        if not scheduler.running:
            return False
        try:
            await asyncio.to_thread(scheduler.get_jobs)
            return True
        except Exception:
            return False

    @classmethod
    async def _check_cache(cls) -> bool:
        try:
            await cache.set("health_check_test_key", "test", ttl=10)
            value = await cache.get("health_check_test_key")
            return value == "test"
        except Exception:
            return False

    @classmethod
    async def _check_bot(cls) -> bool:
        try:
            await bot.get_me()
            return True
        except Exception:
            return False

    @classmethod
    async def check_health(cls) -> HealthSchema:
        return HealthSchema(
            database=await cls._check_database(),
            queue=await cls._check_queue(),
            cache=await cls._check_cache(),
            bot=await cls._check_bot(),
        )

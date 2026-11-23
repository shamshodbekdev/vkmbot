from aiocache import RedisCache
from aiocache.serializers import JsonSerializer

from core.config import config

_redis = config.redis_options

cache: RedisCache = RedisCache(
    namespace=config.telegram_username,
    serializer=JsonSerializer(),
    endpoint=_redis["host"],
    port=_redis["port"],
    db=_redis["db"],
    password=_redis["password"],
    ssl=_redis["ssl"],
)

from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from core.config import config

_redis = config.redis_options
_connect_args = dict(
    host=_redis["host"],
    port=_redis["port"],
    password=_redis["password"],
    ssl=_redis["ssl"],
)
if _redis["username"]:
    _connect_args["username"] = _redis["username"]

# Coroutine jobs run on the bot's event loop (AsyncIOExecutor), so long-running
# jobs such as broadcasts never block polling as long as they await I/O.
scheduler = AsyncIOScheduler(
    jobstores=dict(
        default=RedisJobStore(db=_redis["db"], **_connect_args),
    ),
    job_defaults=dict(
        coalesce=True,
        max_instances=1,
        misfire_grace_time=3600,
    ),
)

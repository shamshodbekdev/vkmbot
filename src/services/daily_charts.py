import logging
from html import escape

from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError

from core.bootstrap import bot
from core.cache import cache
from core.scheduler import scheduler
from keyboard.inline.charts import ChartsKeyboard
from services.youtube.charts import YouTubeCharts
from utils.constants import YOUTUBE_PAGE_SIZE

logger = logging.getLogger(__name__)


def daily_charts_job_id(user_id: int) -> str:
    return "daily_charts_%d" % user_id


def daily_charts_cache_key(user_id: int) -> str:
    return "daily_charts:%d" % user_id


async def send_daily_charts(chat_id: int, user_id: int, country_code: str) -> None:
    """Scheduler job: send the chart for ``country_code`` to the subscribed chat."""
    playlist = await YouTubeCharts.get_playlist(country=country_code)
    if not playlist or not playlist.tracks:
        logger.warning("Daily charts unavailable for %s", country_code)
        return

    limit = YOUTUBE_PAGE_SIZE
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=escape(playlist.title),
            reply_markup=ChartsKeyboard.make(
                tracks=playlist.tracks[:limit],
                offset=0,
                limit=limit,
                total=len(playlist.tracks),
                current=country_code,
                country_page=0,
            ),
        )
    except TelegramForbiddenError:
        # The user blocked the bot: stop sending instead of failing every day.
        logger.info("Daily charts disabled for %s: bot is blocked", user_id)
        try:
            scheduler.remove_job(daily_charts_job_id(user_id))
        except Exception:
            logger.debug("Daily charts job for %s already removed", user_id)
        await cache.delete(daily_charts_cache_key(user_id))
    except TelegramAPIError as error:
        logger.warning("Failed to send daily charts to %s: %s", chat_id, error)

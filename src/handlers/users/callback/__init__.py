from aiogram import Router

from .language import router as language_router
from .check_subscriptions import router as check_subscriptions_router
from .youtube_download import router as youtube_download_router
from .youtube_search import router as youtube_search_router
from .charts import router as charts_router
from .transcription_language import router as transcription_language_router
from .settings import router as settings_router
from .audio_playlist import router as audio_playlist_router
from .playlist import router as playlist_router
from .video_recognize import router as video_recognize_router
from .suggestion import router as suggestion_router
from .mood import router as mood_router
from .bulk_download import router as bulk_download_router
from .close import router as close_router
from .daily_charts import router as daily_charts_router

router = Router()
router.include_router(close_router)
router.include_router(daily_charts_router)
router.include_router(language_router)
router.include_router(check_subscriptions_router)
router.include_router(bulk_download_router)
router.include_router(youtube_download_router)
router.include_router(youtube_search_router)
router.include_router(charts_router)
router.include_router(transcription_language_router)
router.include_router(settings_router)
router.include_router(audio_playlist_router)
router.include_router(playlist_router)
router.include_router(video_recognize_router)
router.include_router(suggestion_router)
router.include_router(mood_router)
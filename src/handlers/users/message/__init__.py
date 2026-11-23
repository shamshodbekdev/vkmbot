from aiogram import Router

from .search import router as search_router
from .voice_recognize import router as voice_recognize_router
from .audio_recognize import router as audio_recognize_router
from .video_recognize import router as video_recognize_router
from .instagram import router as instagram_router
from .tiktok import router as tiktok_router
from .youtube import router as youtube_router

router = Router()
router.include_router(instagram_router)
router.include_router(tiktok_router)
router.include_router(youtube_router)
router.include_router(voice_recognize_router)
router.include_router(audio_recognize_router)
router.include_router(video_recognize_router)
router.include_router(search_router)

from aiogram import Router

from .language import router as language_router
from .start import router as start_router
from .top import router as top_router
from .new import router as new_router
from .mood import router as mood_router
from .settings import router as settings_router
from .my import router as my_router

router = Router()
router.include_router(language_router)
router.include_router(start_router)
router.include_router(top_router)
router.include_router(new_router)
router.include_router(mood_router)
router.include_router(settings_router)
router.include_router(my_router)
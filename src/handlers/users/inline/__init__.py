from aiogram import Router

from .search import router as search_router

router = Router()
router.include_router(search_router)

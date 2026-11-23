from aiogram import Router

from .manage import router as manage_router

router = Router()
router.include_router(manage_router)


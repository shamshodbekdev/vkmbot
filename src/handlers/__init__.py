from aiogram import Router

from .users import router as users_router
from .admin import router as admin_router
from .common import router as common_router

router = Router()
router.include_router(admin_router)
router.include_router(users_router)
router.include_router(common_router)
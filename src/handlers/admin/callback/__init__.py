from aiogram import Router

from .manage_admin import router as manage_admin_router
from .manage_user import router as manage_user_router
from .subscription_manager import router as subscription_manager_router
from .reload import router as reload_router
from .broadcast_history import router as broadcast_history_router

router = Router()
router.include_router(manage_admin_router)
router.include_router(manage_user_router)
router.include_router(subscription_manager_router)
router.include_router(reload_router)
router.include_router(broadcast_history_router)

from aiogram import Router

from .analytics import router as analytics_router
from .broadcast import router as broadcast_router
from .manage_admin import router as manage_admin_router
from .manage_user import router as manage_user_router
from .statistics import router as statistics_router
from .subscription_manager import router as subscription_manager_router

router = Router()
router.include_router(manage_admin_router)
router.include_router(manage_user_router)
router.include_router(statistics_router)
router.include_router(analytics_router)
router.include_router(broadcast_router)
router.include_router(subscription_manager_router)

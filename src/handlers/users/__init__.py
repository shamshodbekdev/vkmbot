from aiogram import Router

from .command import router as command_router
from .callback import router as callback_router
from .message import router as message_router
from .inline import router as inline_router

router = Router()
router.include_router(command_router)
router.include_router(callback_router)
router.include_router(message_router)
router.include_router(inline_router)
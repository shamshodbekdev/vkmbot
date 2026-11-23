from aiogram import Router

from .error import router as error_router
from .my_chat_member import router as my_chat_member_router
from .chat_join_request import router as chat_join_request_router
from .fallback import router as fallback_router

router = Router()
router.include_router(error_router)
router.include_router(my_chat_member_router)
router.include_router(chat_join_request_router)
# Must stay last: it catches every callback query not handled above.
router.include_router(fallback_router)

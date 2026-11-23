import logging

from aiogram import Bot, Router
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.exceptions import TelegramAPIError
from aiogram.types import ChatJoinRequest
from aiogram.utils.i18n import gettext as _

from database.models import User
from keyboard.inline import StartKeyboard

router = Router()
logger = logging.getLogger(__name__)


@router.chat_join_request()
async def chat_join_request_handler(event: ChatJoinRequest, bot: Bot) -> None:
    """Auto-approve join requests and register the user so they can be reached later."""
    await User.get_or_create(
        telegram_id=event.from_user.id,
        defaults=dict(
            chat_type=ChatType.PRIVATE,
            chat_status=ChatMemberStatus.MEMBER,
            is_premium=bool(event.from_user.is_premium),
            display_name=(event.from_user.first_name or str(event.from_user.id))[:255],
        ),
    )
    try:
        await bot.approve_chat_join_request(chat_id=event.chat.id, user_id=event.from_user.id)
    except TelegramAPIError as error:
        logger.warning("Cannot approve join request of %s in %s: %s", event.from_user.id, event.chat.id, error)
        return
    try:
        # user_chat_id lets the bot write first, within 5 minutes of the request.
        await bot.send_message(
            chat_id=event.user_chat_id or event.from_user.id,
            text=_("Hello, world!"),
            reply_markup=StartKeyboard.make(),
        )
    except TelegramAPIError as error:
        logger.info("Cannot greet %s after join request: %s", event.from_user.id, error)

from aiogram import Router
from aiogram.enums import ChatMemberStatus
from aiogram.filters.chat_member_updated import ADMINISTRATOR, KICKED, LEFT, MEMBER, ChatMemberUpdatedFilter
from aiogram.types import ChatMemberUpdated

from database.models import User

router = Router()


async def _set_status(event: ChatMemberUpdated, status: ChatMemberStatus) -> None:
    # Private chats are stored by user id (== chat id), groups by chat id. Using
    # event.from_user here would wrongly hit the admin who removed the bot.
    await User.filter(telegram_id=event.chat.id).update(chat_status=status)


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=LEFT))
async def bot_left_handler(event: ChatMemberUpdated) -> None:
    await _set_status(event, ChatMemberStatus.LEFT)


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=KICKED))
async def bot_kicked_handler(event: ChatMemberUpdated) -> None:
    await _set_status(event, ChatMemberStatus.KICKED)


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=MEMBER))
async def bot_member_handler(event: ChatMemberUpdated) -> None:
    await _set_status(event, ChatMemberStatus.MEMBER)


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=ADMINISTRATOR))
async def bot_promoted_handler(event: ChatMemberUpdated) -> None:
    await _set_status(event, ChatMemberStatus.ADMINISTRATOR)

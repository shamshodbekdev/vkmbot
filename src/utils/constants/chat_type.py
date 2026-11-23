from typing import List, Tuple
from aiogram.enums import ChatMemberStatus

CHAT_TYPES: Tuple[Tuple[str, str, str], ...] = (
    ("private", "Private", "Private ✅"),
    ("group", "Group", "Group ✅"),
    ("supergroup", "Supergroup", "Supergroup ✅"),
)

ACTIVE_STATUSES: List[ChatMemberStatus] = [
    ChatMemberStatus.MEMBER,
    ChatMemberStatus.ADMINISTRATOR,
    ChatMemberStatus.CREATOR,
]

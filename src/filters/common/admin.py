from contextvars import ContextVar
from typing import Optional

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from core.config import config
from database.enums import UserRole
from database.models import User

# Panel roles, lowest to highest. The superadmin is TELEGRAM_ID from .env.
MODERATOR = "moderator"
ADMIN = "admin"
SUPERADMIN = "superadmin"
_RANK = {MODERATOR: 1, ADMIN: 2, SUPERADMIN: 3}

# Role of the sender of the current update, set when a panel filter passes, so the
# reply keyboard can show exactly the sections this person may use.
current_panel_role: ContextVar[str] = ContextVar("current_panel_role", default=ADMIN)


def panel_role(sender_id: int, user: Optional[User]) -> Optional[str]:
    if sender_id == config.telegram_id:
        return SUPERADMIN
    # Rights are personal: in groups ``user`` is the group record, not the sender.
    if user is None or user.telegram_id != sender_id:
        return None
    if user.role == UserRole.ADMINISTRATOR:
        return ADMIN
    if user.role == UserRole.MODERATOR:
        return MODERATOR
    return None


def rank_of(telegram_id: int, user: Optional[User]) -> int:
    """0 for ordinary users, then moderator < admin < superadmin."""
    role = panel_role(telegram_id, user)
    return _RANK[role] if role else 0


class _PanelRoleFilter(BaseFilter):
    minimum: str = ADMIN

    async def __call__(self, event: Message | CallbackQuery, user: Optional[User] = None) -> bool:
        sender = event.from_user
        if sender is None:
            return False
        role = panel_role(sender.id, user)
        if role is None or _RANK[role] < _RANK[self.minimum]:
            return False
        current_panel_role.set(role)
        return True


class IsModerator(_PanelRoleFilter):
    """Moderators, admins and the superadmin: statistics, users, system health."""
    minimum = MODERATOR


class IsAdmin(_PanelRoleFilter):
    """Admins and the superadmin: also broadcasts and mandatory subscriptions."""
    minimum = ADMIN


class IsSuperAdmin(_PanelRoleFilter):
    """Only TELEGRAM_ID: managing the admin team and reading server logs."""
    minimum = SUPERADMIN

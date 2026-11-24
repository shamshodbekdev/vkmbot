import asyncio
import time
from types import SimpleNamespace

from database.enums import UserRole
from filters.common import admin as roles
from keyboard.reply.manage import ManageKeyboard
from services.broadcast.broadcast import _RateLimiter, progress_bar


def test_progress_bar():
    assert progress_bar(0) == "▱" * 12
    assert progress_bar(50) == "▰" * 6 + "▱" * 6
    assert progress_bar(100) == "▰" * 12


def test_rate_limiter_spaces_sends():
    async def run():
        limiter = _RateLimiter(25)
        stamps = []
        for _ in range(50):
            await limiter.acquire()
            stamps.append(time.monotonic())
        return stamps

    stamps = asyncio.run(run())
    # Sliding window: 25 may go at once, the next 25 only a second later,
    # and no 1-second window ever holds more than 25.
    assert stamps[-1] - stamps[0] >= 0.99
    assert max(sum(1 for t in stamps if s <= t < s + 1) for s in stamps) <= 25


def test_panel_roles(monkeypatch):
    monkeypatch.setattr(roles.config, "telegram_id", 1)
    user = lambda tid, role: SimpleNamespace(telegram_id=tid, role=role)
    assert roles.panel_role(1, None) == roles.SUPERADMIN
    assert roles.panel_role(2, user(2, UserRole.ADMINISTRATOR)) == roles.ADMIN
    assert roles.panel_role(3, user(3, UserRole.MODERATOR)) == roles.MODERATOR
    assert roles.panel_role(4, user(4, UserRole.USER)) is None
    # rights are personal: a group record never grants rights to the sender
    assert roles.panel_role(5, user(-100, UserRole.ADMINISTRATOR)) is None
    assert roles.rank_of(1, None) > roles.rank_of(2, user(2, UserRole.ADMINISTRATOR)) > roles.rank_of(3, user(3, UserRole.MODERATOR)) > 0


def test_menu_depends_on_role():
    def texts(role):
        return [b.text for row in ManageKeyboard.make(role).keyboard for b in row]

    assert texts(roles.MODERATOR) == ["Statistics", "Analytics", "Users", "System", "✖️ Close panel"]
    assert "Broadcast message" in texts(roles.ADMIN) and "Admins" not in texts(roles.ADMIN) and "Logs" not in texts(roles.ADMIN)
    assert {"Admins", "Logs"} <= set(texts(roles.SUPERADMIN))


def test_moderator_role_fits_existing_db_column():
    # users.role is varchar(5) in the existing database.
    assert max(len(role.value) for role in UserRole) <= 5

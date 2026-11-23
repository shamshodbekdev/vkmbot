from tortoise import fields, models
from database.enums import UserRole
from aiogram.enums import ChatType, ChatMemberStatus

class User(models.Model):
    id = fields.UUIDField(pk=True)
    
    role: UserRole = fields.CharEnumField(UserRole, default=UserRole.USER)

    telegram_id: int = fields.BigIntField(unique=True)
    display_name: str = fields.CharField(max_length=255)
    language_code: str = fields.CharField(max_length=16, default="uz")
    is_premium: bool = fields.BooleanField(default=False)
    is_blocked: bool = fields.BooleanField(default=False)
    blocked_until = fields.DatetimeField(null=True, default=None)

    chat_status: ChatMemberStatus = fields.CharEnumField(ChatMemberStatus, default=ChatMemberStatus.MEMBER)
    chat_type: ChatType = fields.CharEnumField(ChatType, default=ChatType.PRIVATE)

    created_at: fields.DatetimeField = fields.DatetimeField(auto_now_add=True)
    updated_at: fields.DatetimeField = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "users"
        indexes = [
            ("telegram_id",),
            ("language_code",),
            ("created_at",),
            ("chat_status",),
            ("language_code", "chat_status"),
        ]

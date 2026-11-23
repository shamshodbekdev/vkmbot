from tortoise import fields, models
from aiogram.enums import ChatType

class Subscription(models.Model):
    id = fields.UUIDField(pk=True)

    chat_type: ChatType = fields.CharEnumField(ChatType, default=ChatType.CHANNEL)

    title: str = fields.CharField(max_length=255)
    chat_id: int = fields.BigIntField()
    invite_link: str = fields.CharField(max_length=255, null=True)

    maximum_audience: int = fields.IntField(null=True)
    joined_count: int = fields.IntField(default=0)

    is_active: bool = fields.BooleanField(default=True)

    created_at: fields.DatetimeField = fields.DatetimeField(auto_now_add=True)
    updated_at: fields.DatetimeField = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "subscriptions"
        indexes = [
            ("chat_type", "chat_id")
        ]

class SubscriptionTracker(models.Model):
    id = fields.UUIDField(pk=True)

    subscription: fields.ForeignKeyRelation[Subscription] = fields.ForeignKeyField(
        "models.Subscription",
        related_name="trackers",
        on_delete=fields.CASCADE
    )
    user_id: int = fields.BigIntField()
    is_joined: bool = fields.BooleanField(default=False)

    created_at: fields.DatetimeField = fields.DatetimeField(auto_now_add=True)
    updated_at: fields.DatetimeField = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "subscription_trackers"
        unique_together = [("subscription", "user_id")]
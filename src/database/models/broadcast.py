from tortoise import fields, models


class BroadcastRecord(models.Model):
    id = fields.UUIDField(pk=True)

    languages = fields.JSONField()
    chat_types = fields.JSONField()
    is_premium: bool = fields.BooleanField(default=False)
    mode: str = fields.CharField(max_length=32)

    audience: int = fields.IntField(default=0)
    total: int = fields.IntField(default=0)
    success: int = fields.IntField(default=0)
    failed: int = fields.IntField(default=0)
    blocked: int = fields.IntField(default=0)

    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "broadcast_records"
        ordering = ["-created_at"]

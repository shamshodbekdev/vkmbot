from tortoise import fields, models


class InstagramMedia(models.Model):
    id: fields.UUIDField = fields.UUIDField(pk=True)

    shortcode: str = fields.CharField(max_length=128)
    index_number: int = fields.IntField()
    kind: str = fields.CharField(max_length=8)
    file_id: str = fields.CharField(max_length=255)
    caption: str = fields.CharField(max_length=1024, default="")

    created_at: fields.DatetimeField = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "instagram_media"
        unique_together = [("shortcode", "index_number")]
        indexes = [
            ("shortcode",),
        ]

from tortoise import fields, models


class TikTokMedia(models.Model):
    id: fields.UUIDField = fields.UUIDField(pk=True)

    video_id: str = fields.CharField(max_length=64)
    file_id: str = fields.CharField(max_length=255)

    created_at: fields.DatetimeField = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "tiktok_media"
        unique_together = [("video_id",)]
        indexes = [("video_id",)]

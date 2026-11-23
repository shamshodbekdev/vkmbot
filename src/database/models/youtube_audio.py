from tortoise import fields, models


class YoutubeAudio(models.Model):
    id: fields.UUIDField = fields.UUIDField(pk=True)

    video_id: str = fields.CharField(max_length=32, unique=True)
    file_id: str = fields.CharField(max_length=255)
    title: str = fields.CharField(max_length=255)
    performer: str = fields.CharField(max_length=255)
    duration: int = fields.IntField()
    filesize: int = fields.IntField(default=0)

    created_at: fields.DatetimeField = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "youtube_audios"
        indexes = [
            ("video_id",),
        ]

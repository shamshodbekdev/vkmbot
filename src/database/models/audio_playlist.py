from tortoise import fields, models


class AudioPlaylist(models.Model):
    id: fields.UUIDField = fields.UUIDField(pk=True)

    user: fields.ForeignKeyRelation = fields.ForeignKeyField(
        "models.User", related_name="playlist"
    )
    audio: fields.ForeignKeyRelation = fields.ForeignKeyField(
        "models.YoutubeAudio", related_name="playlists"
    )

    created_at: fields.DatetimeField = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "audio_playlist"
        unique_together = [("user", "audio")]

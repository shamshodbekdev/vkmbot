from tortoise import fields, models


class UserPreferences(models.Model):
    id: fields.UUIDField = fields.UUIDField(pk=True)

    user: fields.ForeignKeyRelation = fields.ForeignKeyField(
        "models.User", related_name="preferences"
    )

    max_results: fields.IntField = fields.IntField(default=10)
    like_buttons: bool = fields.BooleanField(default=True)

    class Meta:
        table = "user_preferences"
        indexes = [("user",)]
        unique_together = [("user",)]
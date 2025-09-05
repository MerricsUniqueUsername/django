from django.db import models
import uuid

class Chat(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    history = models.JSONField(default=list, blank=True)

    def __str__(self):
        return str(self.id)
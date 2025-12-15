from __future__ import annotations

from django.db import models


class TempModel(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    status = models.CharField(
        max_length=12,
        choices=(("new", "New"), ("old", "Old")),
        default="new",
    )
    count = models.IntegerField(default=0)
    note = models.TextField(blank=True, default="")

    def __str__(self) -> str:
        return f"{self.name}"

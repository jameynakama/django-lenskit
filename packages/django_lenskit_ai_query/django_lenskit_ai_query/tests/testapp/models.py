from __future__ import annotations

from django.db import models


class Book(models.Model):
    title = models.CharField(max_length=200)
    year = models.IntegerField(default=2020)

    def __str__(self) -> str:
        return f"{self.title} ({self.year})"

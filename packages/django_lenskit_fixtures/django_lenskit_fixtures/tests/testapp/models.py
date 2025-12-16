from __future__ import annotations

import uuid
from django.db import models


class Root(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)

    def __str__(self) -> str:
        return self.name


class Item(models.Model):
    root = models.ForeignKey(Root, on_delete=models.CASCADE, related_name="items_fk")
    label = models.CharField(max_length=100)


class RootProfile(models.Model):
    root = models.OneToOneField(Root, on_delete=models.CASCADE, related_name="profile")
    notes = models.TextField(blank=True, default="")


# Also a forward M2M from Root to Item
Root.add_to_class("items", models.ManyToManyField(Item, related_name="roots_m2m"))

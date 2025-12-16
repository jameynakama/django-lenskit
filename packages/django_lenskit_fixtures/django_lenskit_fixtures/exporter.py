from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Iterable, Iterator, Optional, Set, Tuple, Type

from django.conf import settings
from django.core import serializers
from django.db import models
from django.db.models.fields.related import ForeignKey, ManyToManyField
from django.db.models.fields.reverse_related import ManyToManyRel, ManyToOneRel


@dataclass(frozen=True)
class ExportConfig:
    include_reverse: bool
    object_limit: int
    fmt: str = "json"


class TooManyObjects(Exception):
    pass


def _default_object_limit() -> int:
    cfg = getattr(settings, "ADMIN_LENSKIT", {}) or {}
    fixtures = (cfg.get("audit") or {}) if False else None  # keep mypy happy
    fixtures = (cfg.get("fixtures") or {}) if isinstance(cfg, dict) else {}
    limit = 5000
    if isinstance(fixtures, dict):
        limit = int(fixtures.get("default_object_limit", limit))
    return limit


def fixtures_enabled() -> bool:
    cfg = getattr(settings, "ADMIN_LENSKIT", {}) or {}
    fixtures = (cfg.get("fixtures") or {}) if isinstance(cfg, dict) else {}
    enabled_value = fixtures.get("enabled")
    if enabled_value is not None:
        return bool(enabled_value)
    return bool(getattr(settings, "DEBUG", False))


def _iter_related_objects(
    obj: models.Model, include_reverse: bool
) -> Iterator[models.Model]:
    for field in obj._meta.get_fields():
        if isinstance(field, ForeignKey):
            target = getattr(obj, field.name, None)
            if target is not None:
                yield target
        elif isinstance(field, ManyToManyField):
            manager = getattr(obj, field.name)
            for target in manager.all():
                yield target

        if include_reverse:
            if isinstance(field, ManyToOneRel):
                rel_manager = getattr(obj, field.get_accessor_name())
                for target in rel_manager.all():
                    yield target
            elif isinstance(field, ManyToManyRel):
                rel_manager = getattr(obj, field.get_accessor_name())
                for target in rel_manager.all():
                    yield target


def build_closure(
    initial: Iterable[models.Model], *, include_reverse: bool, object_limit: int
) -> list[models.Model]:
    queue: deque[models.Model] = deque(initial)
    seen: Set[Tuple[str, object]] = set()
    ordered: list[models.Model] = []

    while queue:
        obj = queue.popleft()
        key = (obj._meta.label_lower, obj.pk)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(obj)
        if len(seen) > object_limit:
            raise TooManyObjects(f"Snapshot exceeded safety limit of {object_limit} objects")

        for rel_obj in _iter_related_objects(obj, include_reverse):
            queue.append(rel_obj)

    return ordered


def serialize_instances(instances: Iterable[models.Model], *, fmt: str) -> str:
    return serializers.serialize(fmt, list(instances), use_natural_foreign_keys=False)


def export_queryset(
    queryset: models.QuerySet[models.Model],
    *,
    include_reverse: bool,
    object_limit: Optional[int] = None,
    fmt: str = "json",
) -> str:
    if not fixtures_enabled():
        raise PermissionError("Fixture export is disabled by configuration")
    limit = object_limit if object_limit is not None else _default_object_limit()
    instances = build_closure(queryset, include_reverse=include_reverse, object_limit=limit)
    return serialize_instances(instances, fmt=fmt)

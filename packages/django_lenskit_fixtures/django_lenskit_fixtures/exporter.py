from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Iterable, Iterator, Optional, Set, Tuple, Type

from django.conf import settings
from django.core import serializers
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import OneToOneField
from django.db.models.fields.related import ForeignKey, ManyToManyField
from django.db.models.fields.reverse_related import ManyToManyRel, ManyToOneRel, OneToOneRel


@dataclass(frozen=True)
class ExportConfig:
    include_reverse: bool
    object_limit: int
    fmt: str = "json"


class TooManyObjects(Exception):
    def __init__(self, limit: int, collected: int, *, at_least: bool = False):
        self.limit = limit
        self.collected = collected
        self.at_least = at_least
        exceed_by = max(collected - limit, 0)
        collected_text = f"at least {collected}" if at_least else f"{collected}"
        super().__init__(f"Snapshot exceeded safety limit of {limit} objects (collected {collected_text}, exceeded by {exceed_by}).")


def _default_object_limit() -> int:
    cfg = getattr(settings, "ADMIN_LENSKIT", {}) or {}
    fixtures_cfg = cfg.get("fixtures") if isinstance(cfg, dict) else None
    default_limit = 5000
    if isinstance(fixtures_cfg, dict):
        try:
            return int(fixtures_cfg.get("default_object_limit", default_limit))
        except Exception:
            return default_limit
    return default_limit


def fixtures_enabled() -> bool:
    cfg = getattr(settings, "ADMIN_LENSKIT", {}) or {}
    fixtures_cfg = cfg.get("fixtures") if isinstance(cfg, dict) else None
    if isinstance(fixtures_cfg, dict):
        enabled_value = fixtures_cfg.get("enabled")
        if enabled_value is not None:
            return bool(enabled_value)
    return bool(getattr(settings, "DEBUG", False))


def _iter_related_objects(
    obj: models.Model, include_reverse: bool
) -> Iterator[models.Model]:
    for field in obj._meta.get_fields():
        # Forward relations
        if isinstance(field, (ForeignKey, OneToOneField)):
            try:
                target = getattr(obj, field.name, None)
            except ObjectDoesNotExist:
                target = None
            if target is not None:
                yield target
        elif isinstance(field, ManyToManyField):
            manager = getattr(obj, field.name)
            for target in manager.all():
                yield target

        if include_reverse:
            # Reverse relations
            if isinstance(field, OneToOneRel):
                try:
                    related_obj = getattr(obj, field.get_accessor_name())
                except ObjectDoesNotExist:
                    related_obj = None
                if related_obj is not None:
                    yield related_obj
            elif isinstance(field, ManyToOneRel):
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
        # Compute next relations first so the probe can include this node's frontier
        next_relations = list(_iter_related_objects(obj, include_reverse))
        seen.add(key)
        ordered.append(obj)
        if len(seen) > object_limit:
            # Probe from both the current queue and this node's immediate frontier
            probe_limit = _excess_probe_limit()
            pending = deque(list(next_relations) + list(queue))
            extra_count, truncated = _probe_excess(pending, include_reverse, seen, probe_limit)
            raise TooManyObjects(
                limit=object_limit,
                collected=len(seen) + extra_count,
                at_least=truncated,
            )

        for rel_obj in next_relations:
            queue.append(rel_obj)

    return ordered


def _excess_probe_limit() -> int:
    cfg = getattr(settings, "ADMIN_LENSKIT", {}) or {}
    fixtures = (cfg.get("fixtures") or {}) if isinstance(cfg, dict) else {}
    default_probe = 2000
    try:
        return int(fixtures.get("excess_probe_limit", default_probe))
    except Exception:
        return default_probe


def _probe_excess(
    queue: deque[models.Model],
    include_reverse: bool,
    seen: Set[Tuple[str, object]],
    probe_limit: int,
) -> tuple[int, bool]:
    # Explore from current boundary without mutating main traversal,
    # counting additional unique objects reachable up to probe_limit.
    pending: deque[models.Model] = deque(queue)
    local_seen: Set[Tuple[str, object]] = set(seen)
    extra = 0
    truncated = False
    while pending and extra < probe_limit:
        obj = pending.popleft()
        for rel in _iter_related_objects(obj, include_reverse):
            key = (rel._meta.label_lower, rel.pk)
            if key in local_seen:
                continue
            local_seen.add(key)
            extra += 1
            if extra >= probe_limit:
                break
            pending.append(rel)
    if pending:
        truncated = True
    return extra, truncated


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

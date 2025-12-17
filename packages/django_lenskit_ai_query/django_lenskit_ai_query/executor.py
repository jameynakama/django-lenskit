from __future__ import annotations

from typing import Any, Dict, List, Tuple

from django.db.models import Model, QuerySet


class ExecutionError(Exception):
    pass


def build_queryset(model: type[Model], spec: Dict[str, Any]) -> QuerySet:
    qs: QuerySet = model._default_manager.all()
    filters = spec.get("filters") or {}
    exclude = spec.get("exclude") or {}
    order_by = spec.get("order_by") or []
    fields = spec.get("fields") or ["pk"]
    limit = int(spec.get("limit") or 50)

    qs = qs.filter(**filters) if filters else qs
    qs = qs.exclude(**exclude) if exclude else qs
    if order_by:
        qs = qs.order_by(*order_by)
    qs = qs.values(*fields)
    return qs[:limit]


def pseudo_code(model: type[Model], spec: Dict[str, Any]) -> str:
    parts: List[str] = [f"{model.__name__}.objects"]
    if spec.get("filters"):
        parts.append(f".filter({repr(spec['filters'])})")
    if spec.get("exclude"):
        parts.append(f".exclude({repr(spec['exclude'])})")
    if spec.get("order_by"):
        parts.append(f".order_by({', '.join(repr(o) for o in spec['order_by'])})")
    fields = spec.get("fields") or ["pk"]
    parts.append(f".values({', '.join(repr(f) for f in fields)})")
    parts.append(f"[:{spec['limit']}]")
    return "".join(parts)

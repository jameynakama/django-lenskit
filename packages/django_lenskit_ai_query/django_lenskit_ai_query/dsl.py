from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from django.apps import apps as django_apps
from django.conf import settings
from django.core.exceptions import FieldDoesNotExist
from django.db.models import Model


ALLOWED_LOOKUPS = {
    "exact",
    "iexact",
    "contains",
    "icontains",
    "in",
    "gt",
    "gte",
    "lt",
    "lte",
    "isnull",
    "startswith",
    "istartswith",
    "endswith",
    "iendswith",
    "range",
    "date",
    "year",
    "month",
    "day",
}


class DslValidationError(Exception):
    pass


def _get_ai_config() -> dict:
    cfg = getattr(settings, "ADMIN_LENSKIT", {}) or {}
    ai = cfg.get("ai_query") if isinstance(cfg, dict) else None
    return ai if isinstance(ai, dict) else {}


def _get_model(model_label: str) -> type[Model]:
    app_label, model_name = model_label.split(".", 1)
    return django_apps.get_model(app_label, model_name)


def _model_allowed(model_label: str) -> bool:
    ai = _get_ai_config()
    allowed = ai.get("allowed_models")
    # Support wildcard to allow all models
    if allowed == "*" or (isinstance(allowed, list) and "*" in allowed):
        return True
    allowed = allowed or []
    return model_label in allowed


def _fields_allowed(model: type[Model], fields: List[str]) -> bool:
    ai = _get_ai_config()
    allowed_fields_cfg = ai.get("allowed_fields") or {}
    allowed_for_model = allowed_fields_cfg.get(f"{model._meta.app_label}.{model._meta.object_name}") or []
    if not allowed_for_model:
        # If not specified, allow any real field path (basic check)
        return True
    # Always allow 'pk' even if not explicitly listed for convenience
    return all((f == "pk") or (f in allowed_for_model) for f in fields)


def _validate_field_path(model: type[Model], field_path: str) -> None:
    # Supports simple __ traversal; stops if any relation is reverse or m2m
    parts = field_path.split("__")
    cur = model
    for i, part in enumerate(parts):
        # Special-case the synthetic 'pk' alias
        if part == "pk":
            # You cannot traverse beyond pk (e.g., pk__something is handled as lookup, not traversal)
            if i < len(parts) - 1:
                # If there are more parts, they should be lookups handled elsewhere; prevent further traversal.
                # Here we just stop traversing as 'pk' is a terminal concrete field alias.
                continue
            # Terminal 'pk' is valid
            break
        try:
            field = cur._meta.get_field(part)
        except FieldDoesNotExist as e:
            raise DslValidationError(f"Unknown field '{part}' in '{field_path}'") from e
        # Disallow reverse/m2m traversal for simplicity (read-only and safe)
        if getattr(field, "many_to_many", False) or getattr(field, "one_to_many", False):
            raise DslValidationError(f"Disallowed reverse/m2m traversal in '{field_path}'")
        # Traverse FK/O2O if not last part
        if i < len(parts) - 1:
            rel = getattr(field, "remote_field", None)
            if not rel or not getattr(rel, "model", None):
                raise DslValidationError(f"Cannot traverse through non-relation '{part}'")
            cur = rel.model


def _validate_lookups(model: type[Model], mapping: Dict[str, Any]) -> None:
    for key in mapping.keys():
        parts = key.split("__")
        if len(parts) >= 2 and parts[-1] in ALLOWED_LOOKUPS:
            base_field = "__".join(parts[:-1])
            _validate_field_path(model, base_field)
        else:
            # No explicit lookup; just a field path → validate it
            _validate_field_path(model, key)


def _max_limit() -> int:
    ai = _get_ai_config()
    return int(ai.get("max_limit", 200))


def _default_limit() -> int:
    ai = _get_ai_config()
    return int(ai.get("default_limit", 50))


def validate_dsl(dsl: Dict[str, Any]) -> Tuple[type[Model], Dict[str, Any]]:
    # Basic schema and key checks
    required = {"model", "limit"}
    optional = {"fields", "filters", "exclude", "order_by"}
    all_allowed = required | optional
    unknown = set(dsl.keys()) - all_allowed
    if unknown:
        raise DslValidationError(f"Unknown keys: {sorted(unknown)}")
    missing = required - set(dsl.keys())
    if missing:
        raise DslValidationError(f"Missing required keys: {sorted(missing)}")

    model_label = dsl["model"]
    if not isinstance(model_label, str) or "." not in model_label:
        raise DslValidationError("Invalid model label")
    if not _model_allowed(model_label):
        raise DslValidationError("Model is not allowed")
    model = _get_model(model_label)

    # Limit
    try:
        limit = int(dsl["limit"])
    except Exception as e:
        raise DslValidationError("Invalid limit") from e
    if limit <= 0 or limit > _max_limit():
        raise DslValidationError("Limit exceeds maximum or is non-positive")

    # Fields
    fields = dsl.get("fields") or ["pk"]
    if not isinstance(fields, list) or not all(isinstance(f, str) for f in fields):
        raise DslValidationError("fields must be a list of strings")
    # Validate field paths and allowlist
    for f in fields:
        _validate_field_path(model, f)
    if not _fields_allowed(model, fields):
        raise DslValidationError("One or more fields are not allowed")

    # Filters / Exclude
    filters = dsl.get("filters") or {}
    exclude = dsl.get("exclude") or {}
    if not isinstance(filters, dict) or not isinstance(exclude, dict):
        raise DslValidationError("filters and exclude must be objects")
    _validate_lookups(model, filters)
    _validate_lookups(model, exclude)

    # Order by
    order_by = dsl.get("order_by") or []
    if not isinstance(order_by, list) or not all(isinstance(o, str) for o in order_by):
        raise DslValidationError("order_by must be a list of strings")
    for ob in order_by:
        base = ob[1:] if ob.startswith("-") else ob
        _validate_field_path(model, base)

    # Build normalized spec
    normalized = {
        "model": model_label,
        "fields": fields,
        "filters": filters,
        "exclude": exclude,
        "order_by": order_by,
        "limit": limit,
    }
    return model, normalized

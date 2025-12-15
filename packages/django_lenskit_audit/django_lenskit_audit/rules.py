from __future__ import annotations

from typing import Optional, Sequence, Type

from django.conf import settings
from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.db import models

from .issues import Issue


class BaseAdminRule:
    code: str
    description: str
    default_severity: str = "warning"

    def check(
        self,
        model: Type[models.Model],
        admin_class: Optional[type[ModelAdmin]],
        site: admin.AdminSite,
    ) -> list[Issue]:  # noqa: D401 - simple interface
        raise NotImplementedError


def _model_label(model: Type[models.Model]) -> str:
    return f"{model._meta.app_label}.{model._meta.object_name}"


def _get_ignore_models() -> set[str]:
    ignore: set[str] = set()
    cfg = getattr(settings, "ADMIN_AUDIT_CONFIG", None)
    if isinstance(cfg, dict):
        ignore.update(cfg.get("ignore_models", []) or [])
    root = getattr(settings, "ADMIN_LENSKIT", None)
    if isinstance(root, dict):
        audit_part = (root.get("audit") or {}).get("config") or {}
        ignore.update(audit_part.get("ignore_models", []) or [])
    return ignore


class ModelNotRegisteredRule(BaseAdminRule):
    code = "MODEL_NOT_REGISTERED"
    description = "Model exists but is not registered in admin."
    default_severity = "info"

    def check(
        self,
        model: Type[models.Model],
        admin_class: Optional[type[ModelAdmin]],
        site: admin.AdminSite,
    ) -> list[Issue]:
        issues: list[Issue] = []
        if admin_class is not None:
            return issues
        meta = model._meta
        if meta.abstract or meta.proxy or getattr(meta, "swapped", False):
            return issues
        ignore = _get_ignore_models()
        if _model_label(model) in ignore:
            return issues
        issues.append(
            Issue(
                severity="info",
                code=self.code,
                message="Model is not registered in admin.",
                hint="Register in admin or add to ignore list.",
                app_label=meta.app_label,
                model_name=meta.object_name,
            )
        )
        return issues


class MissingBasicsRule(BaseAdminRule):
    code = "MISSING_BASICS"
    description = "Admin changelist lacks basic usability options."
    default_severity = "warning"

    TEXT_FIELD_TYPES = (models.CharField, models.TextField, models.EmailField)

    def check(
        self,
        model: Type[models.Model],
        admin_class: Optional[type[ModelAdmin]],
        site: admin.AdminSite,
    ) -> list[Issue]:
        if admin_class is None:
            return []

        issues: list[Issue] = []
        meta = model._meta
        app_label = meta.app_label
        model_name = meta.object_name

        list_display = getattr(admin_class, "list_display", ()) or ()
        search_fields = getattr(admin_class, "search_fields", ()) or ()
        list_filter = getattr(admin_class, "list_filter", ()) or ()

        # Heuristic for missing list_display on non-trivial models
        concrete_fields: Sequence[models.Field] = tuple(meta.concrete_fields)
        if len(concrete_fields) >= 5:
            only_str = tuple(list_display) in ((), ("__str__",), ("__unicode__",))
            if only_str:
                issues.append(
                    Issue(
                        severity="warning",
                        code="MISSING_LIST_DISPLAY",
                        message="Changelist uses only string representation.",
                        hint="Define list_display with key fields.",
                        app_label=app_label,
                        model_name=model_name,
                        admin_class_path=f"{admin_class.__module__}.{admin_class.__name__}",
                    )
                )

        # Missing search_fields when text-like fields exist
        has_text_fields = any(isinstance(f, self.TEXT_FIELD_TYPES) for f in concrete_fields)
        if has_text_fields and not search_fields:
            issues.append(
                Issue(
                    severity="warning",
                    code="MISSING_SEARCH_FIELDS",
                    message="No search_fields defined for text-like fields.",
                    hint="Add search_fields for key text fields.",
                    app_label=app_label,
                    model_name=model_name,
                    admin_class_path=f"{admin_class.__module__}.{admin_class.__name__}",
                )
            )

        # Missing filters when there are booleans or small-choice fields
        def _is_small_choice(field: models.Field) -> bool:
            choices = getattr(field, "choices", None) or ()
            return bool(choices) and len(choices) <= 8

        has_filterable = any(
            isinstance(f, models.BooleanField) or _is_small_choice(f) for f in concrete_fields
        )
        if has_filterable and not list_filter:
            issues.append(
                Issue(
                    severity="warning",
                    code="MISSING_LIST_FILTERS",
                    message="No list_filter defined for filterable fields.",
                    hint="Add list_filter for boolean/choices fields.",
                    app_label=app_label,
                    model_name=model_name,
                    admin_class_path=f"{admin_class.__module__}.{admin_class.__name__}",
                )
            )

        return issues


MODEL_LEVEL_RULES: list[BaseAdminRule] = [ModelNotRegisteredRule()]
ADMIN_LEVEL_RULES: list[BaseAdminRule] = [MissingBasicsRule()]

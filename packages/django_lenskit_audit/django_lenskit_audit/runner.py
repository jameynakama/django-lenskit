from __future__ import annotations

from collections import defaultdict
from typing import Iterable, Optional, Type

from django.apps import apps as django_apps
from django.contrib import admin
from django.db import models

from .issues import Issue
from .rules import ADMIN_LEVEL_RULES, MODEL_LEVEL_RULES


def run_admin_audit(apps: Optional[Iterable[str]] = None) -> list[Issue]:
    apps_scope: Optional[set[str]] = set(apps) if apps else None

    site = admin.site
    registry = site._registry  # type: ignore[attr-defined]  # {model: admin_instance}

    issues: list[Issue] = []

    # 1) Model-level rules (e.g., not registered)
    for model in django_apps.get_models():
        if apps_scope and model._meta.app_label not in apps_scope:
            continue
        admin_instance = registry.get(model)
        admin_class = admin_instance.__class__ if admin_instance is not None else None
        for rule in MODEL_LEVEL_RULES:
            issues.extend(rule.check(model, admin_class, site))

    # 2) Admin-level rules (registered models)
    for model, admin_instance in registry.items():
        if apps_scope and model._meta.app_label not in apps_scope:
            continue
        admin_class = admin_instance.__class__
        for rule in ADMIN_LEVEL_RULES:
            issues.extend(rule.check(model, admin_class, site))

    return issues


def group_issues_for_text(issues: list[Issue]) -> list[tuple[str, list[Issue]]]:
    by_model: dict[str, list[Issue]] = defaultdict(list)
    for issue in issues:
        key = f"{issue.app_label}.{issue.model_name}"
        by_model[key].append(issue)
    return sorted(by_model.items(), key=lambda kv: kv[0])

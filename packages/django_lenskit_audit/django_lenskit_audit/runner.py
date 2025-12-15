from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Iterable, Optional, Type

from django.conf import settings
from django.apps import apps as django_apps
from django.contrib import admin
from django.db import models

from .issues import Issue
from .rules import ADMIN_LEVEL_RULES, MODEL_LEVEL_RULES


def _get_audit_config() -> dict:
    cfg: dict = {}
    root = getattr(settings, "ADMIN_LENSKIT", None)
    if isinstance(root, dict):
        audit_cfg = ((root.get("audit") or {}).get("config") or {})
        if isinstance(audit_cfg, dict):
            cfg.update(audit_cfg)
    return cfg


def _is_first_party_app_label(app_label: str, extra_apps: set[str]) -> bool:
    if app_label in extra_apps:
        return True
    app_config = django_apps.get_app_config(app_label)
    module_name = app_config.module.__name__
    # Exclude Django's own apps quickly
    if module_name.startswith("django."):
        return False
    # Determine project roots
    roots: list[Path] = []
    base_dir = getattr(settings, "BASE_DIR", None)
    if isinstance(base_dir, (str, Path)):
        roots.append(Path(base_dir).resolve())
    cfg = _get_audit_config()
    for p in cfg.get("first_party_paths", []) or []:
        try:
            roots.append(Path(p).resolve())
        except Exception:
            continue
    app_path = Path(app_config.path).resolve()
    return any(str(app_path).startswith(str(root)) for root in roots)


def run_admin_audit(apps: Optional[Iterable[str]] = None, *, first_party_only: Optional[bool] = None) -> list[Issue]:
    apps_scope: Optional[set[str]] = set(apps) if apps else None
    cfg = _get_audit_config()
    if first_party_only is None:
        first_party_only = bool(cfg.get("first_party_only", False))
    first_party_apps_cfg: set[str] = set(cfg.get("first_party_apps", []) or [])

    site = admin.site
    registry = site._registry  # type: ignore[attr-defined]  # {model: admin_instance}

    issues: list[Issue] = []

    # 1) Model-level rules (e.g., not registered)
    for model in django_apps.get_models():
        app_label = model._meta.app_label
        if apps_scope and app_label not in apps_scope:
            continue
        if first_party_only and not _is_first_party_app_label(app_label, first_party_apps_cfg):
            continue
        admin_instance = registry.get(model)
        admin_class = admin_instance.__class__ if admin_instance is not None else None
        for rule in MODEL_LEVEL_RULES:
            issues.extend(rule.check(model, admin_class, site))

    # 2) Admin-level rules (registered models)
    for model, admin_instance in registry.items():
        app_label = model._meta.app_label
        if apps_scope and app_label not in apps_scope:
            continue
        if first_party_only and not _is_first_party_app_label(app_label, first_party_apps_cfg):
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

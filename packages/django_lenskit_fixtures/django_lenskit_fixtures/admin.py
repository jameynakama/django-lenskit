from __future__ import annotations

from django.contrib import admin

from .views import export_action

# Register site-wide action during admin autodiscover
try:
    admin.site.add_action(export_action, name="export_as_fixture")
except Exception:
    pass

# Also inject into each registered ModelAdmin.actions for projects that override get_actions
try:
    for _model, _ma in admin.site._registry.items():
        if getattr(_ma, "actions", None) is None:
            continue
        current = list(_ma.actions or [])
        existing_names = {a if isinstance(a, str) else getattr(a, "__name__", "") for a in current}
        if "export_as_fixture" not in existing_names and "export_action" not in existing_names:
            current.append(export_action)
            _ma.actions = current
except Exception:
    pass

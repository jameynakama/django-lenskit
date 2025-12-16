from __future__ import annotations

from django.contrib import admin

from .views import export_action

# Register site-wide action during admin autodiscover
try:
    admin.site.add_action(export_action, name="export_as_fixture")
except Exception:
    pass

from __future__ import annotations

from django.apps import AppConfig


class FixturesAppConfig(AppConfig):
    name = "django_lenskit_fixtures"
    label = "django_lenskit_fixtures"
    verbose_name = "Django Admin Lenskit - Fixtures"

    def ready(self) -> None:
        # Register a global admin action available on all changelists
        from django.contrib import admin  # local import to avoid early app loading
        from .views import export_action

        try:
            admin.site.add_action(export_action, name="export_as_fixture")
        except Exception:
            # If the action was already registered, ignore
            pass

from __future__ import annotations

from django.apps import AppConfig


class TestAppConfig(AppConfig):
    name = "django_lenskit_audit.tests.testapp"
    label = "testapp"
    verbose_name = "Test App"

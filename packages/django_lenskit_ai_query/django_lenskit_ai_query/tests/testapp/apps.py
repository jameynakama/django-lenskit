from __future__ import annotations

from django.apps import AppConfig


class TestAppConfig(AppConfig):
    name = "django_lenskit_ai_query.tests.testapp"
    label = "ai_test"
    verbose_name = "AI Query Test App"

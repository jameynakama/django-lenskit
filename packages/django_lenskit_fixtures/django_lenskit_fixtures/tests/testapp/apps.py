from __future__ import annotations

from django.apps import AppConfig


class TestFixturesAppConfig(AppConfig):
    name = "django_lenskit_fixtures.tests.testapp"
    label = "fixtures_testapp"
    verbose_name = "Fixtures Test App"

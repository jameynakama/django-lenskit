from __future__ import annotations

from django.apps import apps as django_apps


def test_models_str() -> None:
    Root = django_apps.get_model("fixtures_testapp", "Root")
    r = Root(name="Zed")
    assert str(r) == "Zed"


def test_import_urls_and_wsgi_executes_module_code() -> None:
    import django_lenskit_fixtures.tests.urls as urls  # noqa: F401
    import django_lenskit_fixtures.tests.wsgi as wsgi  # noqa: F401
    assert hasattr(wsgi, "application")



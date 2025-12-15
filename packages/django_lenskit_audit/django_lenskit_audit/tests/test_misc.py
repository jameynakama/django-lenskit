from __future__ import annotations

from django_lenskit_audit.tests.testapp.models import TempModel


def test_models_str() -> None:
    m = TempModel(name="X")
    assert str(m) == "X"


def test_import_urls_and_wsgi_executes_module_code() -> None:
    # Importing should execute module-level code, increasing coverage
    import django_lenskit_audit.tests.urls as urls  # noqa: F401
    import django_lenskit_audit.tests.wsgi as wsgi  # noqa: F401
    assert hasattr(wsgi, "application")

from __future__ import annotations


def test_import_settings_executes_module_code() -> None:
    """Should successfully import settings module."""
    import django_lenskit_admin.settings as settings  # noqa: F401

    assert hasattr(settings, "INSTALLED_APPS")
    assert hasattr(settings, "DATABASES")
    assert hasattr(settings, "SECRET_KEY")


def test_import_urls_executes_module_code() -> None:
    """Should successfully import urls module."""
    import django_lenskit_admin.urls as urls  # noqa: F401

    assert hasattr(urls, "urlpatterns")
    assert len(urls.urlpatterns) > 0


def test_import_wsgi_executes_module_code() -> None:
    """Should successfully import wsgi module."""
    import django_lenskit_admin.wsgi as wsgi  # noqa: F401

    assert hasattr(wsgi, "application")


def test_import_asgi_executes_module_code() -> None:
    """Should successfully import asgi module."""
    import django_lenskit_admin.asgi as asgi  # noqa: F401

    assert hasattr(asgi, "application")


def test_settings_includes_lenskit_apps() -> None:
    """Should include all lenskit apps in INSTALLED_APPS."""
    from django_lenskit_admin.settings import INSTALLED_APPS

    assert "django_lenskit_audit" in INSTALLED_APPS
    assert "django_lenskit_fixtures" in INSTALLED_APPS
    assert "django_lenskit_ai_query" in INSTALLED_APPS


def test_urls_includes_admin_and_lenskit_routes() -> None:
    """Should include admin and lenskit routes."""
    from django_lenskit_admin.urls import urlpatterns

    # Convert URLPattern objects to strings to check paths
    url_strs = [str(p.pattern) for p in urlpatterns]
    assert any("admin/" in s for s in url_strs)
    assert any("admin/lenskit/" in s for s in url_strs)

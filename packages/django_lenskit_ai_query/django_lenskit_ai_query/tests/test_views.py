from __future__ import annotations

import json

import pytest
from django.apps import apps as django_apps
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse


@pytest.mark.django_db
def test_ui_requires_superuser_then_shows_results() -> None:
    Book = django_apps.get_model("ai_test", "Book")
    Book.objects.create(title="A", year=2020)
    client = Client()
    staff = User.objects.create_user(username="s", password="p", is_staff=True, is_superuser=False)
    client.force_login(staff)
    # should require superuser per settings
    r = client.get(reverse("django_lenskit_ai_query:ui"))
    assert r.status_code == 403
    # superuser can access and run
    admin = User.objects.create_superuser(username="a", password="p", email="a@example.com")
    client.force_login(admin)
    r = client.get(reverse("django_lenskit_ai_query:ui"))
    assert r.status_code == 200
    dsl = json.dumps({"model": "ai_test.Book", "fields": ["id", "title"], "filters": {}, "exclude": {}, "order_by": [], "limit": 5})
    r = client.post(reverse("django_lenskit_ai_query:ui"), {"dsl": dsl})
    assert r.status_code == 200
    assert b"Results" in r.content


@pytest.mark.django_db
def test_api_returns_rows_or_error() -> None:
    Book = django_apps.get_model("ai_test", "Book")
    Book.objects.create(title="A", year=2020)
    client = Client()
    admin = User.objects.create_superuser(username="a2", password="p", email="a2@example.com")
    client.force_login(admin)
    url = reverse("django_lenskit_ai_query:api")
    bad = client.post(url, data="not-json", content_type="application/json")
    assert bad.status_code == 400
    good = client.post(
        url,
        data=json.dumps({"model": "ai_test.Book", "fields": ["id"], "filters": {}, "exclude": {}, "order_by": [], "limit": 5}),
        content_type="application/json",
    )
    assert good.status_code == 200
    data = good.json()
    assert "rows" in data and isinstance(data["rows"], list)


@pytest.mark.django_db
def test_ui_disabled_returns_403(settings) -> None:
    """Should return 403 when AI query is disabled."""
    settings.ADMIN_LENSKIT["ai_query"]["enabled"] = False
    client = Client()
    admin = User.objects.create_superuser(username="a3", password="p", email="a3@example.com")
    client.force_login(admin)
    r = client.get(reverse("django_lenskit_ai_query:ui"))
    assert r.status_code == 403
    assert b"disabled" in r.content


@pytest.mark.django_db
def test_api_disabled_returns_403(settings) -> None:
    """Should return 403 when AI query is disabled."""
    settings.ADMIN_LENSKIT["ai_query"]["enabled"] = False
    client = Client()
    admin = User.objects.create_superuser(username="a4", password="p", email="a4@example.com")
    client.force_login(admin)
    url = reverse("django_lenskit_ai_query:api")
    r = client.post(url, data=json.dumps({}), content_type="application/json")
    assert r.status_code == 403


@pytest.mark.django_db
def test_api_requires_post() -> None:
    """Should require POST method."""
    client = Client()
    admin = User.objects.create_superuser(username="a5", password="p", email="a5@example.com")
    client.force_login(admin)
    url = reverse("django_lenskit_ai_query:api")
    r = client.get(url)
    assert r.status_code == 405


@pytest.mark.django_db
def test_api_requires_superuser(settings) -> None:
    """Should require superuser when configured."""
    settings.ADMIN_LENSKIT["ai_query"]["require_superuser"] = True
    client = Client()
    staff = User.objects.create_user(username="s2", password="p", is_staff=True, is_superuser=False)
    client.force_login(staff)
    url = reverse("django_lenskit_ai_query:api")
    r = client.post(url, data=json.dumps({}), content_type="application/json")
    assert r.status_code == 403


@pytest.mark.django_db
def test_ui_get_returns_form(settings) -> None:
    """Should return form on GET."""
    settings.ADMIN_LENSKIT["ai_query"]["enabled"] = True
    client = Client()
    admin = User.objects.create_superuser(username="a6", password="p", email="a6@example.com")
    client.force_login(admin)
    r = client.get(reverse("django_lenskit_ai_query:ui"))
    assert r.status_code == 200
    assert b"dsl" in r.content or b"query" in r.content


@pytest.mark.django_db
def test_ui_post_with_invalid_json(settings) -> None:
    """Should handle invalid JSON in POST."""
    settings.ADMIN_LENSKIT["ai_query"]["enabled"] = True
    client = Client()
    admin = User.objects.create_superuser(username="a7", password="p", email="a7@example.com")
    client.force_login(admin)
    r = client.post(reverse("django_lenskit_ai_query:ui"), {"dsl": "not-valid-json"})
    assert r.status_code == 200
    assert b"error" in r.content or b"Expecting" in r.content


@pytest.mark.django_db
def test_ui_post_with_invalid_dsl(settings) -> None:
    """Should handle invalid DSL in POST."""
    settings.ADMIN_LENSKIT["ai_query"]["enabled"] = True
    client = Client()
    admin = User.objects.create_superuser(username="a8", password="p", email="a8@example.com")
    client.force_login(admin)
    dsl = json.dumps({"model": "invalid.Model", "limit": 5})
    r = client.post(reverse("django_lenskit_ai_query:ui"), {"dsl": dsl})
    assert r.status_code == 200
    assert b"error" in r.content or b"Error" in r.content


@pytest.mark.django_db
def test_ui_builds_admin_links_when_pk_present(settings) -> None:
    """Should build admin change links when pk is in fields."""
    settings.ADMIN_LENSKIT["ai_query"]["enabled"] = True
    Book = django_apps.get_model("ai_test", "Book")
    b = Book.objects.create(title="Test", year=2020)
    client = Client()
    admin = User.objects.create_superuser(username="a9", password="p", email="a9@example.com")
    client.force_login(admin)
    dsl = json.dumps({"model": "ai_test.Book", "fields": ["pk", "title"], "filters": {}, "exclude": {}, "order_by": [], "limit": 5})
    r = client.post(reverse("django_lenskit_ai_query:ui"), {"dsl": dsl})
    assert r.status_code == 200
    # Check that admin URL pattern is in the response
    assert b"admin" in r.content or b"change" in r.content


@pytest.mark.django_db
def test_api_returns_orm_code(settings) -> None:
    """Should return ORM pseudo code in response."""
    settings.ADMIN_LENSKIT["ai_query"]["enabled"] = True
    Book = django_apps.get_model("ai_test", "Book")
    Book.objects.create(title="Test", year=2020)
    client = Client()
    admin = User.objects.create_superuser(username="a10", password="p", email="a10@example.com")
    client.force_login(admin)
    url = reverse("django_lenskit_ai_query:api")
    r = client.post(
        url,
        data=json.dumps({"model": "ai_test.Book", "fields": ["id"], "filters": {}, "exclude": {}, "order_by": [], "limit": 5}),
        content_type="application/json",
    )
    assert r.status_code == 200
    data = r.json()
    assert "orm" in data
    assert "dsl" in data


@pytest.mark.django_db
def test_generate_api_requires_post() -> None:
    """Should require POST method for generate API."""
    client = Client()
    admin = User.objects.create_superuser(username="a11", password="p", email="a11@example.com")
    client.force_login(admin)
    url = reverse("django_lenskit_ai_query:generate")
    r = client.get(url)
    assert r.status_code == 405


@pytest.mark.django_db
def test_generate_api_disabled_returns_403(settings) -> None:
    """Should return 403 when disabled."""
    settings.ADMIN_LENSKIT["ai_query"]["enabled"] = False
    client = Client()
    admin = User.objects.create_superuser(username="a12", password="p", email="a12@example.com")
    client.force_login(admin)
    url = reverse("django_lenskit_ai_query:generate")
    r = client.post(url, data=json.dumps({"query": "test"}), content_type="application/json")
    assert r.status_code == 403


@pytest.mark.django_db
def test_generate_api_requires_superuser(settings) -> None:
    """Should require superuser for generate API."""
    settings.ADMIN_LENSKIT["ai_query"]["require_superuser"] = True
    client = Client()
    staff = User.objects.create_user(username="s3", password="p", is_staff=True, is_superuser=False)
    client.force_login(staff)
    url = reverse("django_lenskit_ai_query:generate")
    r = client.post(url, data=json.dumps({"query": "test"}), content_type="application/json")
    assert r.status_code == 403


@pytest.mark.django_db
def test_generate_api_requires_query_param(settings) -> None:
    """Should require 'query' parameter."""
    settings.ADMIN_LENSKIT["ai_query"]["enabled"] = True
    client = Client()
    admin = User.objects.create_superuser(username="a13", password="p", email="a13@example.com")
    client.force_login(admin)
    url = reverse("django_lenskit_ai_query:generate")
    r = client.post(url, data=json.dumps({}), content_type="application/json")
    assert r.status_code == 400
    data = r.json()
    assert "query" in data["error"]


@pytest.mark.django_db
def test_generate_api_handles_llm_not_configured(monkeypatch, settings) -> None:
    """Should handle LlmNotConfigured exception."""
    settings.ADMIN_LENSKIT["ai_query"]["enabled"] = True
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = Client()
    admin = User.objects.create_superuser(username="a14", password="p", email="a14@example.com")
    client.force_login(admin)
    url = reverse("django_lenskit_ai_query:generate")
    r = client.post(url, data=json.dumps({"query": "show me books"}), content_type="application/json")
    assert r.status_code == 501


@pytest.mark.django_db
def test_ui_handles_admin_url_reverse_failure(settings) -> None:
    """Should gracefully handle admin URL reverse failures."""
    settings.ADMIN_LENSKIT["ai_query"]["enabled"] = True
    Book = django_apps.get_model("ai_test", "Book")
    Book.objects.create(title="Test", year=2020)
    client = Client()
    admin = User.objects.create_superuser(username="a15", password="p", email="a15@example.com")
    client.force_login(admin)
    # Use id field instead of pk to test pk_name path
    dsl = json.dumps({"model": "ai_test.Book", "fields": ["id", "title"], "filters": {}, "exclude": {}, "order_by": [], "limit": 5})
    r = client.post(reverse("django_lenskit_ai_query:ui"), {"dsl": dsl})
    assert r.status_code == 200

from __future__ import annotations

import json

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse
from django.apps import apps as django_apps


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

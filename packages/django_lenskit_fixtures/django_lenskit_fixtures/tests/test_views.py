from __future__ import annotations

import pytest
from django.apps import apps as django_apps
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from django_lenskit_fixtures.views import export_action


@pytest.mark.django_db
def test_export_config_view_get_and_post_flow() -> None:
    Root = django_apps.get_model("fixtures_testapp", "Root")
    r = Root.objects.create(name="R1")

    client = Client()
    user = User.objects.create_user(username="u", password="p", is_staff=True)
    client.force_login(user)

    model_label = f"{Root._meta.app_label}.{Root._meta.model_name}"
    url = reverse("django_lenskit_fixtures:export_config")

    # GET
    resp = client.get(url, {"model": model_label, "pks": str(r.pk)})
    assert resp.status_code == 200
    assert b"Fixture Export" in resp.content

    # POST generate
    resp = client.post(
        url + f"?model={model_label}&pks={r.pk}",
        {"fmt": "json", "include_reverse": "on", "object_limit": 100},
    )
    assert resp.status_code == 200
    assert b"Preview" in resp.content
    # Data present in page
    assert b'["fixtures_testapp.root"' or b'"fixtures_testapp.root"' in resp.content


@pytest.mark.django_db
def test_export_config_view_disabled_returns_400() -> None:
    Root = django_apps.get_model("fixtures_testapp", "Root")
    r = Root.objects.create(name="R1")
    client = Client()
    user = User.objects.create_user(username="u3", password="p", is_staff=True)
    client.force_login(user)
    model_label = f"{Root._meta.app_label}.{Root._meta.model_name}"
    url = reverse("django_lenskit_fixtures:export_config")
    from django.test import override_settings as _ov

    with _ov(ADMIN_LENSKIT={"fixtures": {"enabled": False}}):
        assert client.get(url, {"model": model_label, "pks": str(r.pk)}).status_code == 400


@pytest.mark.django_db
def test_export_config_view_invalid_model_format_returns_400() -> None:
    client = Client()
    user = User.objects.create_user(username="u4", password="p", is_staff=True)
    client.force_login(user)
    url = reverse("django_lenskit_fixtures:export_config")
    assert client.get(url, {"model": "invalid", "pks": "1"}).status_code == 400


@pytest.mark.django_db
def test_export_config_view_invalid_limit_is_ignored() -> None:
    Root = django_apps.get_model("fixtures_testapp", "Root")
    r = Root.objects.create(name="R1")
    client = Client()
    user = User.objects.create_user(username="u5", password="p", is_staff=True)
    client.force_login(user)
    model_label = f"{Root._meta.app_label}.{Root._meta.model_name}"
    url = reverse("django_lenskit_fixtures:export_config")
    resp = client.get(url, {"model": model_label, "pks": str(r.pk), "limit": "abc"})
    assert resp.status_code == 200


@pytest.mark.django_db
def test_export_config_view_post_too_many_objects_shows_error() -> None:
    Root = django_apps.get_model("fixtures_testapp", "Root")
    Item = django_apps.get_model("fixtures_testapp", "Item")
    RootProfile = django_apps.get_model("fixtures_testapp", "RootProfile")
    r = Root.objects.create(name="R1")
    i1 = Item.objects.create(root=r, label="i1")
    r.items.add(i1)
    RootProfile.objects.create(root=r, notes="p")
    client = Client()
    user = User.objects.create_user(username="u6", password="p", is_staff=True)
    client.force_login(user)
    model_label = f"{Root._meta.app_label}.{Root._meta.model_name}"
    url = reverse("django_lenskit_fixtures:export_config")
    resp = client.post(
        url + f"?model={model_label}&pks={r.pk}",
        {"fmt": "json", "include_reverse": "on", "object_limit": 1},
    )
    assert resp.status_code == 200
    assert b"exceeded" in resp.content


@pytest.mark.django_db
def test_export_config_view_post_download_response_headers() -> None:
    Root = django_apps.get_model("fixtures_testapp", "Root")
    r = Root.objects.create(name="R1")
    client = Client()
    user = User.objects.create_user(username="u7", password="p", is_staff=True)
    client.force_login(user)
    model_label = f"{Root._meta.app_label}.{Root._meta.model_name}"
    url = reverse("django_lenskit_fixtures:export_config")
    resp = client.post(
        url + f"?model={model_label}&pks={r.pk}",
        {"fmt": "json", "include_reverse": "", "object_limit": 100, "download": "1"},
    )
    assert resp.status_code == 200
    cd = resp.headers.get("Content-Disposition", "")
    assert "attachment;" in cd and "_fixture.json" in cd


@pytest.mark.django_db
def test_export_action_redirect_builds_params() -> None:
    Root = django_apps.get_model("fixtures_testapp", "Root")
    r = Root.objects.create(name="R1")
    qs = Root.objects.filter(pk=r.pk)
    resp = export_action(None, None, qs)
    loc = resp["Location"]
    assert "model=fixtures_testapp.root" in loc
    assert f"pks={r.pk}" in loc


@pytest.mark.django_db
def test_invalid_params_return_400() -> None:
    client = Client()
    user = User.objects.create_user(username="u2", password="p", is_staff=True)
    client.force_login(user)
    url = reverse("django_lenskit_fixtures:export_config")
    # Missing model
    assert client.get(url).status_code == 400
    # Invalid model
    assert client.get(url, {"model": "x.y", "pks": "1"}).status_code == 400
    # Empty pks
    Root = django_apps.get_model("fixtures_testapp", "Root")
    model_label = f"{Root._meta.app_label}.{Root._meta.model_name}"
    assert client.get(url, {"model": model_label, "pks": ""}).status_code == 400

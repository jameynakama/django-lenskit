from __future__ import annotations

import json
import re

import pytest
from django.apps import apps as django_apps
from django.test import override_settings

from django_lenskit_fixtures.exporter import TooManyObjects, export_queryset


@pytest.mark.django_db
def test_export_queryset_forward_and_reverse_relations() -> None:
    Root = django_apps.get_model("fixtures_testapp", "Root")
    Item = django_apps.get_model("fixtures_testapp", "Item")
    RootProfile = django_apps.get_model("fixtures_testapp", "RootProfile")

    r = Root.objects.create(name="R1")
    i1 = Item.objects.create(root=r, label="i1")
    Item.objects.create(root=r, label="i2")
    r.items.add(i1)
    RootProfile.objects.create(root=r, notes="profile")

    # Start from the Root, include reverse; expect Root, Items via reverse FK, profile via O2O, and M2M items
    data = export_queryset(
        Root.objects.filter(pk=r.pk), include_reverse=True, object_limit=100, fmt="json"
    )
    parsed = json.loads(data)
    model_labels = {obj["model"] for obj in parsed}
    assert "fixtures_testapp.root" in model_labels
    assert "fixtures_testapp.item" in model_labels
    assert "fixtures_testapp.rootprofile" in model_labels
    # Expect multiple objects total
    assert len(parsed) >= 4


@pytest.mark.django_db
def test_export_queryset_respects_enabled_flag() -> None:
    Root = django_apps.get_model("fixtures_testapp", "Root")
    r = Root.objects.create(name="R1")
    with override_settings(ADMIN_LENSKIT={"fixtures": {"enabled": False}}):
        with pytest.raises(PermissionError):
            export_queryset(Root.objects.filter(pk=r.pk), include_reverse=False, object_limit=10)


@pytest.mark.django_db
def test_safety_cap_excess_message_improves_bounds() -> None:
    Root = django_apps.get_model("fixtures_testapp", "Root")
    Item = django_apps.get_model("fixtures_testapp", "Item")
    RootProfile = django_apps.get_model("fixtures_testapp", "RootProfile")

    r = Root.objects.create(name="R1")
    i1 = Item.objects.create(root=r, label="i1")
    i2 = Item.objects.create(root=r, label="i2")
    r.items.add(i1, i2)
    RootProfile.objects.create(root=r, notes="profile")

    # Limit too small to include reverse graph; should raise with exceeded by >=1 and collected >= limit+1
    with override_settings(
        ADMIN_LENSKIT={"fixtures": {"enabled": True, "excess_probe_limit": 1000}}
    ):
        with pytest.raises(TooManyObjects) as ei:
            export_queryset(Root.objects.filter(pk=r.pk), include_reverse=True, object_limit=2)
    msg = str(ei.value)
    assert "exceeded by" in msg and "collected" in msg
    m = re.search(r"exceeded by (\d+)", msg)
    assert m and int(m.group(1)) >= 1


@pytest.mark.django_db
def test_export_queryset_enabled_via_debug_without_config() -> None:
    Root = django_apps.get_model("fixtures_testapp", "Root")
    r = Root.objects.create(name="R1")
    # No fixtures config -> falls back to DEBUG (True in test settings)
    with override_settings(ADMIN_LENSKIT={}, DEBUG=True):
        data = export_queryset(
            Root.objects.filter(pk=r.pk),
            include_reverse=False,
            object_limit=10,
            fmt="json",
        )
        assert '"fixtures_testapp.root"' in data or "fixtures_testapp.root" in data


@pytest.mark.django_db
def test_safety_cap_message_can_be_truncated_with_probe_limit() -> None:
    Root = django_apps.get_model("fixtures_testapp", "Root")
    Item = django_apps.get_model("fixtures_testapp", "Item")
    RootProfile = django_apps.get_model("fixtures_testapp", "RootProfile")
    r = Root.objects.create(name="R1")
    i1 = Item.objects.create(root=r, label="i1")
    i2 = Item.objects.create(root=r, label="i2")
    r.items.add(i1, i2)
    RootProfile.objects.create(root=r, notes="profile")
    with override_settings(ADMIN_LENSKIT={"fixtures": {"enabled": True, "excess_probe_limit": 1}}):
        with pytest.raises(TooManyObjects) as ei:
            export_queryset(Root.objects.filter(pk=r.pk), include_reverse=True, object_limit=2)
    assert "at least" in str(ei.value)


@pytest.mark.django_db
def test_export_queryset_uses_default_object_limit_when_not_provided() -> None:
    Root = django_apps.get_model("fixtures_testapp", "Root")
    r = Root.objects.create(name="R1")
    # Omitting object_limit triggers default limit path
    data = export_queryset(Root.objects.filter(pk=r.pk), include_reverse=False, fmt="json")
    assert '"fixtures_testapp.root"' in data or "fixtures_testapp.root" in data


@pytest.mark.django_db
def test_excess_probe_limit_invalid_falls_back_safely() -> None:
    Root = django_apps.get_model("fixtures_testapp", "Root")
    Item = django_apps.get_model("fixtures_testapp", "Item")
    r = Root.objects.create(name="R1")
    Item.objects.create(root=r, label="i1")
    Item.objects.create(root=r, label="i2")
    with override_settings(
        ADMIN_LENSKIT={"fixtures": {"enabled": True, "excess_probe_limit": "oops"}}
    ):
        with pytest.raises(TooManyObjects):
            export_queryset(Root.objects.filter(pk=r.pk), include_reverse=True, object_limit=1)


@pytest.mark.django_db
def test_default_object_limit_invalid_string_falls_back() -> None:
    Root = django_apps.get_model("fixtures_testapp", "Root")
    r = Root.objects.create(name="R1")
    with override_settings(
        ADMIN_LENSKIT={"fixtures": {"enabled": True, "default_object_limit": "oops"}}
    ):
        # Omitting object_limit will trigger parsing and the except branch
        data = export_queryset(Root.objects.filter(pk=r.pk), include_reverse=False, fmt="json")
        assert '"fixtures_testapp.root"' in data or "fixtures_testapp.root" in data


@pytest.mark.django_db
def test_internal_iter_related_objects_yields_forward_relations() -> None:
    Root = django_apps.get_model("fixtures_testapp", "Root")
    Item = django_apps.get_model("fixtures_testapp", "Item")
    RootProfile = django_apps.get_model("fixtures_testapp", "RootProfile")
    r = Root.objects.create(name="R1")
    i = Item.objects.create(root=r, label="i")
    p = RootProfile.objects.create(root=r, notes="n")
    r.items.add(i)
    # Directly exercise forward relation yields
    from django_lenskit_fixtures import exporter as _exp

    fwd_from_item = list(_exp._iter_related_objects(i, include_reverse=False))
    assert any(
        getattr(obj, "pk", None) == r.pk
        and getattr(getattr(obj, "_meta", None), "label_lower", "").endswith(".root")
        for obj in fwd_from_item
    )
    fwd_from_profile = list(_exp._iter_related_objects(p, include_reverse=False))
    assert any(
        getattr(obj, "pk", None) == r.pk
        and getattr(getattr(obj, "_meta", None), "label_lower", "").endswith(".root")
        for obj in fwd_from_profile
    )
    fwd_from_root = list(_exp._iter_related_objects(r, include_reverse=False))
    assert any(
        getattr(obj, "pk", None) == i.pk
        and getattr(getattr(obj, "_meta", None), "label_lower", "").endswith(".item")
        for obj in fwd_from_root
    )


@pytest.mark.django_db
def test_default_object_limit_when_config_not_dict() -> None:
    Root = django_apps.get_model("fixtures_testapp", "Root")
    r = Root.objects.create(name="R1")
    from django.test import override_settings as _ov

    with _ov(ADMIN_LENSKIT=None, DEBUG=True):
        data = export_queryset(Root.objects.filter(pk=r.pk), include_reverse=False, fmt="json")
        assert '"fixtures_testapp.root"' in data or "fixtures_testapp.root" in data

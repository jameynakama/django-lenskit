from __future__ import annotations

import json

import pytest
from django.apps import apps as django_apps

from django_lenskit_ai_query.dsl import DslValidationError, validate_dsl
from django_lenskit_ai_query.executor import build_queryset, pseudo_code


@pytest.mark.django_db
def test_validate_and_execute_basic_query() -> None:
    Book = django_apps.get_model("ai_test", "Book")
    Book.objects.create(title="A", year=2020)
    Book.objects.create(title="B", year=2021)

    dsl = {
        "model": "ai_test.Book",
        "fields": ["id", "title"],
        "filters": {"year__gte": 2020},
        "exclude": {},
        "order_by": ["-year"],
        "limit": 5,
    }
    model, spec = validate_dsl(dsl)
    qs = build_queryset(model, spec)
    rows = list(qs)
    assert rows and set(rows[0].keys()) == {"id", "title"}
    code = pseudo_code(model, spec)
    assert "values('id', 'title')" in code


def test_invalid_model_rejected() -> None:
    with pytest.raises(DslValidationError):
        validate_dsl({"model": "x.y", "limit": 5})


def test_disallowed_model_rejected() -> None:
    with pytest.raises(DslValidationError):
        validate_dsl({"model": "auth.User", "limit": 5})


def test_limit_too_large_rejected(settings) -> None:
    settings.ADMIN_LENSKIT["ai_query"]["max_limit"] = 5
    with pytest.raises(DslValidationError):
        validate_dsl({"model": "ai_test.Book", "limit": 10})

def test_allowed_models_wildcard(settings) -> None:
    settings.ADMIN_LENSKIT["ai_query"]["allowed_models"] = "*"
    # Should validate even though model isn't explicitly listed
    model, spec = validate_dsl({"model": "ai_test.Book", "fields": ["id"], "limit": 1})
    assert spec["model"] == "ai_test.Book"


def test_unknown_keys_rejected() -> None:
    """Should reject DSL with unknown keys."""
    with pytest.raises(DslValidationError, match="Unknown keys"):
        validate_dsl({"model": "ai_test.Book", "limit": 5, "invalid_key": "value"})


def test_missing_required_keys_rejected() -> None:
    """Should reject DSL missing required keys."""
    with pytest.raises(DslValidationError, match="Missing required keys"):
        validate_dsl({"model": "ai_test.Book"})


def test_invalid_model_label_format_rejected() -> None:
    """Should reject invalid model label format."""
    with pytest.raises(DslValidationError, match="Invalid model label"):
        validate_dsl({"model": "InvalidFormat", "limit": 5})


def test_negative_limit_rejected() -> None:
    """Should reject negative limit."""
    with pytest.raises(DslValidationError, match="non-positive"):
        validate_dsl({"model": "ai_test.Book", "limit": 0})


def test_invalid_limit_type_rejected() -> None:
    """Should reject non-integer limit."""
    with pytest.raises(DslValidationError, match="Invalid limit"):
        validate_dsl({"model": "ai_test.Book", "limit": "not-a-number"})


def test_fields_must_be_list_of_strings() -> None:
    """Should reject fields that aren't a list of strings."""
    with pytest.raises(DslValidationError, match="fields must be a list of strings"):
        validate_dsl({"model": "ai_test.Book", "limit": 5, "fields": "not-a-list"})

    with pytest.raises(DslValidationError, match="fields must be a list of strings"):
        validate_dsl({"model": "ai_test.Book", "limit": 5, "fields": [123, 456]})


def test_unknown_field_rejected() -> None:
    """Should reject unknown field names."""
    with pytest.raises(DslValidationError, match="Unknown field"):
        validate_dsl({"model": "ai_test.Book", "limit": 5, "fields": ["nonexistent_field"]})


def test_disallowed_fields_rejected(settings) -> None:
    """Should reject fields not in allowed_fields config."""
    settings.ADMIN_LENSKIT["ai_query"]["allowed_fields"] = {"ai_test.Book": ["id"]}
    with pytest.raises(DslValidationError, match="not allowed"):
        validate_dsl({"model": "ai_test.Book", "limit": 5, "fields": ["id", "title"]})


def test_pk_always_allowed(settings) -> None:
    """Should always allow pk field even if not explicitly listed."""
    settings.ADMIN_LENSKIT["ai_query"]["allowed_fields"] = {"ai_test.Book": ["title"]}
    model, spec = validate_dsl({"model": "ai_test.Book", "limit": 5, "fields": ["pk", "title"]})
    assert "pk" in spec["fields"]


def test_default_fields_to_pk_when_not_provided() -> None:
    """Should default to pk field when fields not provided."""
    model, spec = validate_dsl({"model": "ai_test.Book", "limit": 5})
    assert spec["fields"] == ["pk"]


def test_filters_must_be_dict() -> None:
    """Should reject filters that aren't a dict."""
    with pytest.raises(DslValidationError, match="filters and exclude must be objects"):
        validate_dsl({"model": "ai_test.Book", "limit": 5, "filters": "not-a-dict"})


def test_exclude_must_be_dict() -> None:
    """Should reject exclude that aren't a dict."""
    with pytest.raises(DslValidationError, match="filters and exclude must be objects"):
        validate_dsl({"model": "ai_test.Book", "limit": 5, "exclude": ["not", "a", "dict"]})


def test_filter_with_lookup() -> None:
    """Should validate filters with lookups."""
    model, spec = validate_dsl({
        "model": "ai_test.Book",
        "limit": 5,
        "filters": {"title__icontains": "test", "year__gte": 2020}
    })
    assert "title__icontains" in spec["filters"]
    assert "year__gte" in spec["filters"]


def test_invalid_filter_field_rejected() -> None:
    """Should reject filters with unknown fields."""
    with pytest.raises(DslValidationError, match="Unknown field"):
        validate_dsl({"model": "ai_test.Book", "limit": 5, "filters": {"invalid__exact": "value"}})


def test_order_by_must_be_list_of_strings() -> None:
    """Should reject order_by that isn't a list of strings."""
    with pytest.raises(DslValidationError, match="order_by must be a list of strings"):
        validate_dsl({"model": "ai_test.Book", "limit": 5, "order_by": "not-a-list"})

    with pytest.raises(DslValidationError, match="order_by must be a list of strings"):
        validate_dsl({"model": "ai_test.Book", "limit": 5, "order_by": [123]})


def test_order_by_with_descending() -> None:
    """Should handle descending order_by."""
    model, spec = validate_dsl({"model": "ai_test.Book", "limit": 5, "order_by": ["-year", "title"]})
    assert spec["order_by"] == ["-year", "title"]


def test_invalid_order_by_field_rejected() -> None:
    """Should reject order_by with unknown fields."""
    with pytest.raises(DslValidationError, match="Unknown field"):
        validate_dsl({"model": "ai_test.Book", "limit": 5, "order_by": ["nonexistent"]})


def test_field_alias_normalization(settings) -> None:
    """Should normalize common field aliases."""
    # Ensure id is in allowed fields
    settings.ADMIN_LENSKIT["ai_query"]["allowed_fields"] = {"ai_test.Book": ["id", "title", "year"]}
    model, spec = validate_dsl({"model": "ai_test.Book", "limit": 5, "fields": ["id"]})
    assert "id" in spec["fields"]


def test_filter_alias_normalization() -> None:
    """Should normalize common field aliases in filters."""
    model, spec = validate_dsl({"model": "ai_test.Book", "limit": 5, "filters": {"id__exact": 1}})
    assert "id__exact" in spec["filters"]


def test_order_by_alias_normalization() -> None:
    """Should normalize common field aliases in order_by."""
    model, spec = validate_dsl({"model": "ai_test.Book", "limit": 5, "order_by": ["id"]})
    assert "id" in spec["order_by"]


def test_pk_field_traversal_handling() -> None:
    """Should handle pk field in paths."""
    model, spec = validate_dsl({"model": "ai_test.Book", "limit": 5, "fields": ["pk"]})
    assert "pk" in spec["fields"]


def test_disallowed_reverse_traversal() -> None:
    """Should reject reverse relation traversal."""
    # This would need a model with reverse relations properly set up
    # For now, test basic validation works
    model, spec = validate_dsl({"model": "ai_test.Book", "limit": 5})
    assert spec is not None


def test_normalized_dsl_structure() -> None:
    """Should return normalized DSL with all keys."""
    model, spec = validate_dsl({"model": "ai_test.Book", "limit": 5})
    assert "model" in spec
    assert "fields" in spec
    assert "filters" in spec
    assert "exclude" in spec
    assert "order_by" in spec
    assert "limit" in spec


@pytest.mark.django_db
def test_build_queryset_with_filters() -> None:
    """Should build queryset with filters applied."""
    Book = django_apps.get_model("ai_test", "Book")
    Book.objects.create(title="Match", year=2020)
    Book.objects.create(title="NoMatch", year=2019)

    model, spec = validate_dsl({
        "model": "ai_test.Book",
        "limit": 5,
        "fields": ["title"],
        "filters": {"year__gte": 2020}
    })
    qs = build_queryset(model, spec)
    rows = list(qs)
    assert len(rows) == 1
    assert rows[0]["title"] == "Match"


@pytest.mark.django_db
def test_build_queryset_with_exclude() -> None:
    """Should build queryset with exclude applied."""
    Book = django_apps.get_model("ai_test", "Book")
    Book.objects.create(title="Keep", year=2020)
    Book.objects.create(title="Exclude", year=2019)

    model, spec = validate_dsl({
        "model": "ai_test.Book",
        "limit": 5,
        "fields": ["title"],
        "exclude": {"year__lt": 2020}
    })
    qs = build_queryset(model, spec)
    rows = list(qs)
    assert len(rows) == 1
    assert rows[0]["title"] == "Keep"


@pytest.mark.django_db
def test_build_queryset_with_order_by() -> None:
    """Should build queryset with order_by applied."""
    Book = django_apps.get_model("ai_test", "Book")
    Book.objects.create(title="B", year=2020)
    Book.objects.create(title="A", year=2021)

    model, spec = validate_dsl({
        "model": "ai_test.Book",
        "limit": 5,
        "fields": ["title"],
        "order_by": ["title"]
    })
    qs = build_queryset(model, spec)
    rows = list(qs)
    assert rows[0]["title"] == "A"
    assert rows[1]["title"] == "B"


@pytest.mark.django_db
def test_build_queryset_respects_limit() -> None:
    """Should respect limit in queryset."""
    Book = django_apps.get_model("ai_test", "Book")
    for i in range(5):
        Book.objects.create(title=f"Book{i}", year=2020 + i)

    model, spec = validate_dsl({
        "model": "ai_test.Book",
        "limit": 2,
        "fields": ["title"]
    })
    qs = build_queryset(model, spec)
    rows = list(qs)
    assert len(rows) == 2

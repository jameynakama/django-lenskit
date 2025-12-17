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
        "limit": 10,
    }
    model, spec = validate_dsl(dsl)
    qs = build_queryset(model, spec)
    rows = list(qs)
    assert rows and set(rows[0].keys()) == {"id", "title"}
    code = pseudo_code(model, spec)
    assert "values('id', 'title')" in code


def test_invalid_model_rejected() -> None:
    with pytest.raises(DslValidationError):
        validate_dsl({"model": "x.y", "limit": 10})


def test_disallowed_model_rejected() -> None:
    with pytest.raises(DslValidationError):
        validate_dsl({"model": "auth.User", "limit": 10})


def test_limit_too_large_rejected(settings) -> None:
    settings.ADMIN_LENSKIT["ai_query"]["max_limit"] = 5
    with pytest.raises(DslValidationError):
        validate_dsl({"model": "ai_test.Book", "limit": 10})

from __future__ import annotations

from django.apps import apps as django_apps
from django.contrib.admin import ModelAdmin
from django.test import override_settings

from django_lenskit_audit.issues import Issue
from django_lenskit_audit.rules import (
    ADMIN_LEVEL_RULES,
    MODEL_LEVEL_RULES,
    MissingBasicsRule,
    ModelNotRegisteredRule,
)


def test_model_not_registered_rule_flags_issue() -> None:
    model = django_apps.get_model("testapp", "TempModel")
    rule = ModelNotRegisteredRule()
    issues = rule.check(model, None, None)  # type: ignore[arg-type]
    assert any(i.code == "MODEL_NOT_REGISTERED" for i in issues)


@override_settings(
    ADMIN_LENSKIT={
        "audit": {
            "config": {
                "ignore_models": ["testapp.TempModel"],
            }
        }
    }
)
def test_model_not_registered_rule_respects_ignore_list() -> None:
    model = django_apps.get_model("testapp", "TempModel")
    rule = ModelNotRegisteredRule()
    issues = rule.check(model, None, None)  # type: ignore[arg-type]
    assert issues == []

def test_missing_basics_rule_ignores_when_no_admin_class() -> None:
    model = django_apps.get_model("testapp", "TempModel")
    rule = MissingBasicsRule()
    issues = rule.check(model, None, None)  # type: ignore[arg-type]
    assert issues == []


def test_missing_basics_rule_flags_all() -> None:
    model = django_apps.get_model("testapp", "TempModel")

    class _Admin(ModelAdmin):
        list_display = ()
        search_fields = ()
        list_filter = ()

    rule = MissingBasicsRule()
    issues = rule.check(model, _Admin, None)  # type: ignore[arg-type]
    codes = {i.code for i in issues}
    assert "MISSING_LIST_DISPLAY" in codes
    assert "MISSING_SEARCH_FIELDS" in codes
    assert "MISSING_LIST_FILTERS" in codes

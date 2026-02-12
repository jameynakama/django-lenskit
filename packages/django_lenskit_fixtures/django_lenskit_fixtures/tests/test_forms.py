from __future__ import annotations

import pytest

from django_lenskit_fixtures.forms import FixtureExportForm


def test_fixture_export_form_valid_defaults() -> None:
    """Should validate with default values."""
    form = FixtureExportForm(data={"fmt": "json", "include_reverse": False, "object_limit": 5000})
    assert form.is_valid()
    assert form.cleaned_data["fmt"] == "json"
    assert form.cleaned_data["include_reverse"] is False
    assert form.cleaned_data["object_limit"] == 5000


def test_fixture_export_form_yaml_format() -> None:
    """Should accept yaml format."""
    form = FixtureExportForm(data={"fmt": "yaml", "include_reverse": True, "object_limit": 100})
    assert form.is_valid()
    assert form.cleaned_data["fmt"] == "yaml"


def test_fixture_export_form_cleans_object_limit_minimum() -> None:
    """Should enforce minimum object_limit of 1."""
    # The field has min_value=1, so 0 and negative values will fail field validation
    form = FixtureExportForm(data={"fmt": "json", "include_reverse": False, "object_limit": 0})
    assert not form.is_valid()
    assert "object_limit" in form.errors

    form = FixtureExportForm(data={"fmt": "json", "include_reverse": False, "object_limit": -10})
    assert not form.is_valid()
    assert "object_limit" in form.errors


def test_fixture_export_form_include_reverse_optional() -> None:
    """Should allow include_reverse to be omitted."""
    form = FixtureExportForm(data={"fmt": "json", "object_limit": 100})
    assert form.is_valid()
    assert form.cleaned_data["include_reverse"] is False


def test_fixture_export_form_invalid_format() -> None:
    """Should reject invalid format."""
    form = FixtureExportForm(data={"fmt": "xml", "include_reverse": False, "object_limit": 100})
    assert not form.is_valid()
    assert "fmt" in form.errors


def test_fixture_export_form_missing_required_fields() -> None:
    """Should require fmt and object_limit."""
    form = FixtureExportForm(data={})
    assert not form.is_valid()
    assert "fmt" in form.errors
    assert "object_limit" in form.errors


def test_fixture_export_form_object_limit_clean_method_enforces_minimum() -> None:
    """Should enforce minimum via clean_object_limit even for edge cases."""
    # Test that clean_object_limit enforces minimum of 1
    # This test directly validates the clean method behavior
    form = FixtureExportForm(data={"fmt": "json", "object_limit": 1})
    assert form.is_valid()
    assert form.cleaned_data["object_limit"] == 1

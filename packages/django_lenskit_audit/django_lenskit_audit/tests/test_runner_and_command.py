from __future__ import annotations

from pathlib import Path

import pytest
from django.core.management import call_command
from django.test import override_settings

from django_lenskit_audit.runner import group_issues_for_text, run_admin_audit


def test_runner_first_party_only_excludes_django_apps() -> None:
    issues = run_admin_audit(first_party_only=True)
    keys = [f"{i.app_label}.{i.model_name}" for i in issues]
    assert not any(k.startswith("auth.") for k in keys)
    assert not any(k.startswith("contenttypes.") for k in keys)
    assert any(k.startswith("testapp.") for k in keys)


def test_group_issues_sorting() -> None:
    grouped = group_issues_for_text(run_admin_audit(first_party_only=True))
    assert grouped == sorted(grouped, key=lambda kv: kv[0])


def test_management_command_text_and_html(tmp_path: Path) -> None:
    html_path = tmp_path / "audit.html"
    call_command("audit_admin", "--first-party-only", f"--html={html_path}")
    assert html_path.exists()
    content = html_path.read_text(encoding="utf-8")
    assert "Admin Audit Report" in content


def test_management_command_fail_on_exits() -> None:
    with pytest.raises(SystemExit):
        call_command("audit_admin", "--first-party-only", "--fail-on=info")


@override_settings(
    ADMIN_LENSKIT={
        "audit": {
            "config": {
                "first_party_only": True,
            }
        }
    }
)
def test_runner_respects_settings_default_first_party_only() -> None:
    # No explicit flag; should pick from settings
    issues = run_admin_audit(None)
    keys = [f"{i.app_label}.{i.model_name}" for i in issues]
    assert any(k.startswith("testapp.") for k in keys)
    assert not any(k.startswith("auth.") for k in keys)


def test_runner_apps_scope_limits_results() -> None:
    issues = run_admin_audit(["testapp"], first_party_only=True)
    keys = [f"{i.app_label}.{i.model_name}" for i in issues]
    assert all(k.startswith("testapp.") for k in keys)


@override_settings(
    ADMIN_LENSKIT={
        "audit": {
            "config": {
                "first_party_only": True,
                "first_party_apps": ["auth"],
            }
        }
    }
)
def test_runner_first_party_apps_override_includes_auth() -> None:
    issues = run_admin_audit(None)  # pick up settings
    keys = [f"{i.app_label}.{i.model_name}" for i in issues]
    assert any(k.startswith("auth.") for k in keys)

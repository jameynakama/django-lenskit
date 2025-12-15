from __future__ import annotations

from typing import Any, Optional

from django.core.management.base import BaseCommand, CommandParser
from django.template.loader import render_to_string

from ...runner import group_issues_for_text, run_admin_audit

SEVERITY_ORDER = {"info": 0, "warning": 1, "error": 2}


class Command(BaseCommand):  # type: ignore[misc]
    help = "Analyze Django admin configuration and flag potential issues."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--html", dest="html_path", help="Write HTML report to this path")
        parser.add_argument(
            "--fail-on",
            dest="fail_on",
            choices=["info", "warning", "error"],
            help="Exit non-zero if issues at or above this level are found",
        )
        parser.add_argument(
            "--apps",
            dest="apps",
            help="Comma-separated list of app labels to scope the audit",
        )

    def handle(self, *args: str, **options: Any) -> None:
        apps_arg: Optional[str] = options.get("apps")
        app_labels: Optional[list[str]] = apps_arg.split(",") if apps_arg else None
        issues = run_admin_audit(app_labels)

        # Print text summary
        for model_key, model_issues in group_issues_for_text(issues):
            for iss in sorted(
                model_issues, key=lambda i: SEVERITY_ORDER.get(i.severity, 0), reverse=True
            ):
                self.stdout.write(
                    f"[{model_key}] ({iss.severity}) {iss.code}: {iss.message}"
                    + (f"\n  Hint: {iss.hint}" if iss.hint else "")
                )

        # Optional HTML
        html_path: Optional[str] = options.get("html_path")
        if html_path:
            html = render_to_string(
                "admin_lenskit/audit_report.html",
                {
                    "issues": issues,
                    "grouped": group_issues_for_text(issues),
                },
            )
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)
            self.stdout.write(self.style.SUCCESS(f"Wrote HTML report to {html_path}"))

        # Optional fail-on
        fail_on: Optional[str] = options.get("fail_on")
        if fail_on:
            threshold = SEVERITY_ORDER[fail_on]
            if any(SEVERITY_ORDER.get(i.severity, 0) >= threshold for i in issues):
                raise SystemExit(1)

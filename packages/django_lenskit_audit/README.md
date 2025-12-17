django-lenskit-audit
====================

Admin audit and cleanup checks for Django Admin.

What it does
- Flags models not registered in admin.
- Detects basic changelist usability gaps: missing list_display, search_fields, list_filter.
- Optional first-party filtering so you can focus on your apps (not Django’s).
- CLI report to stdout; optional HTML report.

Install
- Local (editable):
  - pip install -e .
  - or uv pip install -e .
- From Git:
  - pip install "git+https://github.com/jameynakama/lenskit@main#subdirectory=packages/django_lenskit_audit"

Setup
- Add to INSTALLED_APPS:
  INSTALLED_APPS += ["django_lenskit_audit"]
- Optional settings (settings.py):
  ADMIN_LENSKIT = {
      "audit": {
          "config": {
              "first_party_only": True,
              "first_party_paths": [],    # extra project roots
              "first_party_apps": [],     # explicit inclusions
              "ignore_models": ["auth.Permission", "contenttypes.ContentType"],
          }
      }
  }

Usage
- Basic:
  python manage.py audit_admin
- Scope:
  python manage.py audit_admin --apps=app1,app2
- Include third-party:
  python manage.py audit_admin --all-apps
- Force first-party only (overrides settings):
  python manage.py audit_admin --first-party-only
- HTML report:
  python manage.py audit_admin --html=admin_audit.html
- CI gating:
  python manage.py audit_admin --fail-on=warning

Tests
- Install extras:
  uv pip install -e '.[test]'
- Run:
  pytest -q --cov=django_lenskit_audit --cov-report=term-missing

Notes
- Rules are intentionally heuristic — hints, not hard failures.
- You can extend with additional rules in future versions (e.g., N+1 hints).

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
  - pip install "git+<https://github.com/jameynakama/lenskit@main#subdirectory=packages/django_lenskit_audit>"

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

Future rules (roadmap)

- Coverage/metadata
  - Unregistered concrete/proxy models; missing `__str__`/`__repr__`; missing/odd `verbose_name(_plural)`; missing `Meta.ordering`.
- Usability gaps
  - Trivial `list_display`; missing `search_fields`; missing `list_filter`; missing `ordering`/`date_hierarchy`; no `list_per_page`/`show_full_result_count=False`; audit fields not in `readonly_fields`; inlines without `extra=0`.
- Performance smells
  - Related lookups in `list_display` without `list_select_related`; heavy M2M use without `prefetch_related`/`autocomplete_fields`; large FKs without `autocomplete_fields`/`raw_id_fields`; `icontains` on unindexed fields; `date_hierarchy` on non‑indexed field.
- Safety/correctness
  - `save_model`/`delete_model`/`get_queryset` override without `super()`; over‑permissive `has_*_permission`; admin actions lacking permission gating or `short_description`; `get_readonly_fields` not checking `obj`.
- Consistency/duplication
  - Duplicate admin configs across apps (suggest mixins); conflicting `Meta.ordering` vs `ModelAdmin.ordering`.
- Security/PII hygiene
  - PII fields in `list_display`/`search_fields` without explicit allowlist; custom admin views missing CSRF.
- Indexing hints (advisory)
  - Filters/search on non‑indexed columns (suggest `db_index=True`/functional index).
- API ergonomics
  - Missing `empty_value_display`; `SimpleListFilter` candidates for common ad‑hoc filters.
- Framework fit/finish
  - `filter_horizontal/vertical` on huge M2Ms (prefer autocomplete); legacy `raw_id_fields` where `autocomplete_fields` is available.

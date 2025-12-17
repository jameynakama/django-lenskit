django-lenskit-fixtures
=======================

Relation-aware fixture exporter for Django Admin with safety caps.

What it does
- Builds a closure of required objects to ensure loaddata won’t fail on missing FK/M2M targets.
- Traversal:
  - Always follows forward FKs and forward M2Ms.
  - Optional reverse FKs and reverse M2Ms (hierarchy export).
- Safety:
  - Object-limit cap to prevent accidental huge exports.
  - Error message estimates how far you exceeded the cap.
- Output: JSON (default) or YAML (requires PyYAML).

Install
- Local (editable):
  - pip install -e .
  - or uv pip install -e .
- From Git:
  - pip install "git+https://github.com/jameynakama/lenskit@main#subdirectory=packages/django_lenskit_fixtures"

Setup
- Add to INSTALLED_APPS and include URLs:
  INSTALLED_APPS += ["django_lenskit_fixtures"]
  from django.urls import include, path
  urlpatterns += [path("admin/lenskit/", include("django_lenskit_fixtures.urls"))]
- Add the action explicitly on the ModelAdmin(s) you want (recommended):
  from django_lenskit_fixtures.views import export_action
  @admin.register(YourModel)
  class YourModelAdmin(admin.ModelAdmin):
      actions = [export_action]
- Optional settings (settings.py):
  ADMIN_LENSKIT = {
      "fixtures": {
          "enabled": True,             # default: DEBUG
          "default_object_limit": 5000,
          "excess_probe_limit": 2000,  # estimate how many beyond the cap (bounded)
      }
  }

Use
- In the admin changelist:
  1) Select records
  2) Choose action “Export as fixture…”
  3) Configure:
     - Format (JSON/YAML), include reverse relations, object cap
  4) Preview or download
- The exporter deduplicates objects and includes through-table rows for M2Ms.

Production notes
- By default, export is enabled in DEBUG.
  - In production, set ADMIN_LENSKIT['fixtures']['enabled'] to True to allow exports.
  - Keep object caps conservative in prod.

Tests
- Install extras:
  uv pip install -e '.[test]'
- Run:
  pytest -q --ds=django_lenskit_fixtures.tests.settings --cov=django_lenskit_fixtures --cov-report=term-missing

django-admin-lenskit
====================

A set of modular tools to improve Django Admin ergonomics and safety:

- Audit: static/dynamic checks to surface admin misconfigurations and UX/perf smells.
- Fixtures: relation-aware fixture export with safety caps.
- AI Query Builder: read-only natural-language query helper (coming later).

Each tool ships as its own installable Django app. Install only what you need.

Quick links

- packages/django_lenskit_audit — Admin audit tool
- packages/django_lenskit_fixtures — Fixture exporter

Install

- Local path (editable):
  - pip:
    - pip install -e packages/django_lenskit_audit
    - pip install -e packages/django_lenskit_fixtures
  - uv:
    - uv pip install -e packages/django_lenskit_audit
    - uv pip install -e packages/django_lenskit_fixtures
- From Git (subdirectory):
  - pip install "git+<https://github.com/jameynakama/lenskit@main#subdirectory=packages/django_lenskit_audit>"
  - pip install "git+<https://github.com/jameynakama/lenskit@main#subdirectory=packages/django_lenskit_fixtures>"

Audit — quickstart

1) Add to INSTALLED_APPS:
   INSTALLED_APPS += ["django_lenskit_audit"]
2) Run:
   python manage.py audit_admin
   python manage.py audit_admin --apps=app1,app2
   python manage.py audit_admin --html=admin_audit.html
   python manage.py audit_admin --fail-on=warning
3) Optional settings (settings.py):
   ADMIN_LENSKIT = {
       "audit": {
           "config": {
               "first_party_only": True,
               "first_party_paths": [],       # extra project roots, if needed
               "first_party_apps": [],        # explicit inclusions
               "ignore_models": ["auth.Permission", "contenttypes.ContentType"],
           }
       }
   }

Fixtures — quickstart

1) Add to INSTALLED_APPS and include URLs:
   INSTALLED_APPS += ["django_lenskit_fixtures"]
   from django.urls import include, path
   urlpatterns += [path("admin/lenskit/", include("django_lenskit_fixtures.urls"))]
2) Add the export action to any ModelAdmin you want (recommended):
   from django_lenskit_fixtures.views import export_action
   @admin.register(YourModel)
   class YourModelAdmin(admin.ModelAdmin):
       actions = [export_action]
3) Optional settings (settings.py):
   ADMIN_LENSKIT = {
       "fixtures": {
           "enabled": True,            # default: DEBUG
           "default_object_limit": 5000,
           "excess_probe_limit": 2000, # estimate how many beyond the cap (bounded)
       }
   }
4) Use:
   - In a changelist: select objects → action "Export as fixture…"
   - Configure: JSON/YAML, include reverse relations, safety cap
   - Preview or download
   Notes:
   - Reverse relations include reverse FKs and reverse M2Ms.
   - Safety cap prevents accidental huge exports; error includes how far you exceeded.
   - YAML output requires PyYAML installed in your environment.

Testing

- Install test extras:
  - uv pip install -e packages/django_lenskit_audit[test]
  - uv pip install -e packages/django_lenskit_fixtures[test]
- Run:
  - Audit:     pytest -q packages/django_lenskit_audit
  - Fixtures:  pytest -q --ds=django_lenskit_fixtures.tests.settings packages/django_lenskit_fixtures
- Coverage (examples):
  - Audit:     pytest -q packages/django_lenskit_audit --cov=django_lenskit_audit --cov-report=term-missing
  - Fixtures:  pytest -q --ds=django_lenskit_fixtures.tests.settings packages/django_lenskit_fixtures --cov=django_lenskit_fixtures --cov-report=term-missing

Devcontainers (optional)

- For testing inside project devcontainers, either:
  - Install via Git subdirectory inside the container, or
  - Bind mount the repo and install editable (-e) from the mount.

Status

- Audit: MVP implemented (CLI + basic rules), tests included.
- Fixtures: MVP implemented (action + config view + traversal + caps), tests included.
- AI Query Builder: planned.

# django-admin-health-kit — Project Overview

A modular Django app providing enhanced tooling for Django Admin, similar to `django-extensions`, but specifically focused on:

- admin quality,
- data ergonomics,
- safe introspection,
- developer productivity.

It includes three major components:

1. **Fixture Exporter** — relation-aware fixture snapshots (safe, integrity-preserving).
2. **Admin Audit Tool** — static/dynamic checks to find admin misconfigurations, UX issues, and perf smells.
3. **AI Query Builder (Read-Only)** — natural-language → validated read-only ORM queries.

Each module is optional and enabled through settings.

---

## Project Structure (Proposed)

```zsh
admin_health_kit/
    __init__.py
    apps.py
    settings.py
    fixtures_export/
        exporter.py
        admin.py
        views.py
        urls.py
    audit/
        rules.py
        runner.py
        issues.py
        management/commands/audit_admin.py
        templates/admin_health_kit/audit_report.html
    ai_query/
        dsl.py
        parser.py
        executor.py
        views.py
        urls.py
```

---

## Modules Summary

### 1. Fixture Exporter

- Admin action: "Export as fixture…"
- Traversal:
  - Always follows forward FKs and forward M2Ms.
  - Optional: reverse FKs + reverse M2Ms for full hierarchies.
- Safety:
  - Object-limit cap (e.g. 5k).
  - Disabled in production unless explicitly enabled.
- Output:
  - JSON or YAML fixtures.
  - Guarantees `loaddata` will not fail due to missing FK targets.

---

### 2. Admin Audit Tool

Entry point: `python manage.py audit_admin`

Detects:

- Models not registered in admin.
- Admins with:
  - missing `list_display`,
  - missing `search_fields`,
  - missing `list_filter`.
- Possible N+1 issues (complex relations in list_display but no `list_select_related`).
- Duplicated admin configs (suggest mixins).
- Risky overrides (e.g. `save_model` without calling `super`).

Outputs:

- Plain text summary
- Optional HTML report

---

### 3. AI Query Builder (Read-Only)

- Natural language → **strict JSON DSL** describing a read-only ORM query.
- Server validates DSL (model, fields, lookups, limits).
- **No updates, deletes, raw SQL, or arbitrary code.**
- Executes using Django ORM and returns:
  - DSL preview,
  - ORM pseudo-code,
  - Row-limited table.

Used for debugging, introspection, and analytics inside admin.

---

## Settings Example

```python
ADMIN_HEALTH_KIT = {
    "fixtures": {
        "enabled": True,
        "default_object_limit": 5000,
    },
    "audit": {
        "enabled": True,
        "config": {
            "ignore_models": ["auth.Permission", "contenttypes.ContentType"],
        },
    },
    "ai_query": {
        "enabled": True,
        "allowed_models": [
            "auth.User",
            "orders.Order",
        ],
        "allowed_fields": {},
        "max_limit": 200,
        "default_limit": 50,
        "require_superuser": True,
    }
}
```

---

## Vision

**django-admin-health-kit** gives Django teams a toolkit for:

- cleaner admin UIs,
- safer data handling,
- faster debugging workflows,
- more discoverable schemas,
- and a smoother local/dev environment setup.

Designed to be **modular**, **safe**, **ergonomic**, and **drop-in**.

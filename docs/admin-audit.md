# Django Admin Audit / Cleanup Bot — Spec Summary

## Goal

Provide a tool (management command + optional HTML report) that analyzes Django admin configuration and flags:

- Missing admin coverage
- Usability problems (hard-to-use changelists/forms)
- Performance smells (obvious N+1 risks, etc.)
- Repeated patterns that should be shared via mixins

The focus is static/dynamic inspection of `ModelAdmin` and models, not generic linting of Python code.

---

## Entry Points

### 1. Management Command

Command name: `python manage.py audit_admin`

Outputs:

- Human-readable text summary to stdout (for quick runs)
- Optionally writes an HTML report to a file (e.g. `admin_audit_report.html`)

Arguments:

- `--html=PATH` (write HTML report)
- `--fail-on=LEVEL` (e.g. `warning` or `error` → non-zero exit code; useful for CI)
- `--apps=app1,app2` (limit to specific apps)
- `--settings=path.to.CustomConfig` (optional custom config object)

### 2. Optional Admin Integration

Optional admin view that:

- Reads latest report (or runs the audit on demand)
- Displays results grouped by app/model/rule
- Links to relevant admin URLs (e.g. change list and change form)

This can be a follow-up; MVP is the management command.

---

## Audit Architecture

### Core Concepts

- **Rule**: a class that inspects Django admin + model metadata and returns a list of "issues".
- **Issue**: a structured object with:
  - `severity` (`"info" | "warning" | "error"`)
  - `code` (stable identifier, e.g. `"MISSING_LIST_DISPLAY"`)
  - `message` (human-readable)
  - `hint` (optional recommendation)
  - `app_label`, `model_name`
  - `admin_class_path` (if applicable)
  - `details` (extra dict data usable in HTML rendering)

- **Runner**: collects all registered rules, runs them, aggregates issues, and formats output.

### Rule Interface (conceptual)

```python
class BaseAdminRule:
    code: str  # e.g. "MISSING_LIST_DISPLAY"
    description: str
    default_severity: str = "warning"

    def check(self, model, admin_class, site) -> list[Issue]:
        """Return a list of Issue objects for this (model, admin_class)."""
        raise NotImplementedError
```

Rules are auto-registered via a simple registry list or decorator.

The runner iterates over:

- All registered `ModelAdmin` in each `AdminSite` (most projects just use `site = admin.site`).
- All concrete models in `apps.get_models()` to detect models not registered in admin.

---

## Data Available to Rules

For each model/admin pair:

- `model._meta` (fields, relations, verbose names, etc.)
- `admin_class`:
  - `list_display`, `list_filter`, `search_fields`, `autocomplete_fields`, `readonly_fields`, `list_select_related`, `ordering`, etc.
  - overridden methods: `get_queryset`, `save_model`, `get_search_results`, etc. (via introspection)

Possible dynamic bits (optional):

- For specific rules, sample a small subset of rows (e.g. count of rows for FKs).
- But the MVP can be entirely static.

---

## Planned Rules (MVP Set)

You can start with a small but high-value rule set.

### 1. Unregistered Models

**Problem:** Models exist but are not registered in admin.

Heuristic:

- For each `model` in `apps.get_models()`:
  - If concrete and not abstract.
  - Not in ignore list.
  - And not registered in `admin.site._registry`.

Emit `Issue`:

- `code = "MODEL_NOT_REGISTERED"`
- Severity: `"info"` (or `"warning"` if you want to be aggressive)
- Hint: "Consider registering this model in admin or adding it to the ignore list."

Config:

- `ADMIN_AUDIT_IGNORE_MODELS = ["auth.Permission", "contenttypes.ContentType", ...]`

---

### 2. Changelist Missing Basic Usability

#### a) Missing list_display

If a model has more than N fields (e.g. 5+) and `list_display` is empty or only `("__str__",)`:

- `code = "MISSING_LIST_DISPLAY"`
- Message: "Changelist relies entirely on the string representation."
- Hint: "Define list_display with key identifying fields."

#### b) No search fields on searchable models

If there are text-like fields (`CharField`, `TextField`, `EmailField`, etc.) and `search_fields` is empty:

- `code = "MISSING_SEARCH_FIELDS"`

#### c) No filters on enum-ish fields

If model has small-choice fields (`choices` defined) or bool fields and `list_filter` is empty:

- `code = "MISSING_LIST_FILTERS"`

---

### 3. Autocomplete and Foreign Keys

#### a) Large FK without autocomplete

If an FK field is used in `raw_id_fields` or just in the form, but:

- Approx row count for related model is large (e.g. > 1,000); and
- The FK is not in `autocomplete_fields`;

Then:

- `code = "MISSING_AUTOCOMPLETE"`
- Hint: "For large relations, enable autocomplete_fields to make this usable."

Note: For MVP, you can skip actual counting and just flag FKs not in `autocomplete_fields` as an info-level suggestion.

---

### 4. Performance Smells in Changelists

#### a) list_display uses many related fields but no list_select_related

If `list_display` includes attributes that look like FK traversals (`"user__email"`, `"profile__city"`), but:

- `list_select_related` is not set or is an empty tuple,

Flag:

- `code = "POSSIBLE_N_PLUS_ONE_IN_LIST"`
- Severity: `"warning"`

Heuristic is intentionally approximate: you’re hinting, not proving.

---

### 5. Repeated Admin Config (mixins candidate)

Detect admin classes that repeat the same configuration:

- identical `list_filter`, `search_fields`, `readonly_fields`, etc. across multiple admin classes.

Flag:

- `code = "DUPLICATED_ADMIN_CONFIG"`
- Message: "This admin configuration is repeated across N classes."
- Hint: "Consider extracting a shared mixin."

Implementation:

- Hash a subset of configuration (e.g. a tuple of key attributes); group by this hash.

---

### 6. Potentially Risky Overrides

#### a) `save_model` override without calling super

If an admin class overrides `save_model` and the method body source does *not* contain `"super("`:

- `code = "SAVEMODEL_NO_SUPER"`
- Severity: `"warning"` or `"error"` depending on taste.
- Hint: "Ensure default behavior isn’t bypassed unintentionally."

This requires optional source inspection (via `inspect.getsource`) and catching failures gracefully (no hard dependency).

---

## Configuration

Global settings (all optional):

```python
ADMIN_AUDIT_CONFIG = {
    "ignore_models": [
        "auth.Permission",
        "contenttypes.ContentType",
    ],
    "severity_overrides": {
        "MODEL_NOT_REGISTERED": "info",
        "SAVEMODEL_NO_SUPER": "error",
    },
    "object_count_cutoffs": {
        "large_fk_threshold": 1000,
    },
}
```

Additionally:

- `ADMIN_AUDIT_APPS = ["myapp", "otherapp"]` to scope the audit.
- `ADMIN_AUDIT_SITE = "django.contrib.admin.site"` (customizable if using multiple sites).

---

## Output Formats

### Text (stdout)

Grouped by app → model:

Example:

```bash
[myapp.Book] (warning) MISSING_LIST_DISPLAY:
  Changelist relies entirely on the string representation.
  Hint: Define list_display with key identifying fields.

[myapp.Book] (info) MODEL_NOT_REGISTERED:
  Model is not registered in admin.
```

### HTML (file)

Rendered sections:

- Summary: counts by severity + rule code.
- Details by app/model.
- Color-coded severity tags.
- Optional link to corresponding admin URLs (e.g. `/admin/myapp/book/`).

A simple Django template can be used for rendering when `--html` is provided.

---

## Implementation Skeleton (Conceptual)

- App: `admin_audit/`
  - `__init__.py`
  - `rules.py` (rule implementations)
  - `runner.py` (collects rules, runs them, returns issues)
  - `issues.py` (Issue dataclass)
  - `management/commands/audit_admin.py` (CLI entry)
  - `templates/admin_audit/report.html` (optional)

Runner pseudocode:

```python
def run_admin_audit(config) -> list[Issue]:
    site = admin.site  # or custom
    registry = site._registry  # dict {model: admin_instance}

    issues = []

    # 1) model-level rules (unregistered, etc.)
    all_models = apps.get_models()
    for model in all_models:
        admin_class = registry.get(model)
        for rule in MODEL_LEVEL_RULES:
            issues.extend(rule.check(model, admin_class, site))

    # 2) admin-registered rules
    for model, admin_instance in registry.items():
        admin_class = admin_instance.__class__
        for rule in ADMIN_LEVEL_RULES:
            issues.extend(rule.check(model, admin_class, site))

    return issues
```

---

## MVP Scope (Hackathon-Friendly)

You can deliver a very compelling MVP by implementing:

1. Management command with:
   - Unregistered models rule
   - Missing `list_display`
   - Missing `search_fields`
   - Missing `list_filter`
2. Basic stdout output.
3. Optional: one "fun" rule like duplicated config or N+1 hint.

Then, if time allows:

- Add HTML report rendering.
- Add severity overrides and ignore lists.
- Add risky overrides detection.

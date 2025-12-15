# Admin Lenskit — AI Query Builder (Read-Only) Specification

## Goal

Provide a safe, natural-language interface inside Django admin that produces **validated, read-only Django ORM queries**.

The system outputs:

- JSON DSL describing the query,
- ORM pseudo-code,
- A limited-read result table.

Absolutely **no write operations** are permitted.

---

## 1. Workflow

1. User navigates to `/admin/admin-lenskit/ai-query/`.
2. User types a natural-language query:
   - "Show me the 100 most recent users from Oregon."
3. Backend:
   - Provides schema + allowed models to the LLM.
   - LLM outputs **only a JSON DSL object**.
4. Backend validates DSL against model metadata.
5. If valid:
   - Executes read-only ORM query.
   - Renders results + DSL + ORM snippet.
6. If invalid:
   - Rejects with reason.
   - Never executes anything.

---

## 2. JSON DSL Schema

LLM must output a JSON object of this exact form:

```json
{
  "model": "app_label.ModelName",
  "fields": ["id", "email", "created_at"],
  "filters": {
    "created_at__gte": "2024-01-01"
  },
  "exclude": {},
  "order_by": ["-created_at"],
  "limit": 50
}
```

### Required Keys

- `model`
- `limit`

### Optional

- `fields` (defaults to ["pk"])
- `filters`
- `exclude`
- `order_by`

### Forbidden

- Any unrecognized keys
- Any write references
- Any raw SQL
- Any ORM methods except:
  - `filter`, `exclude`, `order_by`
  - slicing (limit)
  - `values()`

---

## 3. Validation Rules

The backend must validate:

### Model

- Model must be in `ADMIN_LENSKIT["ai_query"]["allowed_models"]`.

### Fields

- Each field in `fields` must:
  - exist on model, or
  - be a valid `__`-traversal.
- Sensitive fields may be excluded via `allowed_fields`.

### Filters / Exclude

- Keys must be valid Django lookups:
  - Example: `email__icontains`, `created_at__gte`
- Reject dangerous lookups (e.g. regex) if desired.

### Limit

- Must be an int.
- Must be <= `max_limit` (e.g. 200).

### Ordering

- strip leading `-` and check field exists.
- no functions, no SQL fragments.

If any step fails → error, no execution.

---

## 4. ORM Execution Layer

Conceptual implementation:

```python
rows = (
    Model.objects
        .filter(**spec["filters"])
        .exclude(**spec["exclude"])
        .order_by(*spec["order_by"])
        .values(*spec["fields"])
)[:spec["limit"]]
```

Disallowed ORM calls (MUST NOT appear anywhere):

- `update()`
- `delete()`
- `create()` or `bulk_create()`
- `raw()`
- `extra()`

Always enforce row limit and safe access.

---

## 5. Admin UI

The admin view shows:

### Input

- Textarea: "Your query"
- Dropdown for target model (optional hint to LLM)
- Limit selector (optional)

### Output

- JSON DSL (pretty-printed)
- ORM pseudo-code snippet, e.g.:

  ```python
  User.objects
      .filter(is_active=True)
      .order_by("-date_joined")[:50]
  ```

- Results table (limited)

### Permissions

- `is_superuser` or custom `can_query_ai` permission.
- Optionally disabled in production.

---

## 6. Settings

```python
ADMIN_LENSKIT = {
    "ai_query": {
        "enabled": True,
        "allowed_models": [
            "auth.User",
            "shop.Order",
        ],
        "allowed_fields": {},
        "max_limit": 200,
        "default_limit": 50,
        "require_superuser": True,
    }
}
```

---

## 7. Safety Measures

- Hard limit on rows returned.
- Strict whitelist of models.
- Optional whitelist of fields.
- Reject unexpected DSL keys.
- Reject DSL values containing:
  - SQL keywords,
  - Python keywords,
  - suspicious tokens (optional heuristic).

---

## 8. MVP Scope

- Admin view with:
  - natural query input
  - DSL output
  - ORM pseudo-code output
  - table results
- Strict DSL schema
- Validation + read-only executor
- Support for 1–2 models
- Guardrails + permissions

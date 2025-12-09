# Django Admin Fixture Export — Spec Summary

## Goal

Provide an admin feature that exports selected objects (or configured sets of objects) as Django fixtures, guaranteeing `loaddata` will not fail due to missing FK targets, and optionally including related child objects.

---

## Core Behavior

### 1. Roots

The export starts from a set of **root objects**:

- Selected rows via an admin action, **or**
- Predefined sets from a "snapshot builder" view.

Roots are the starting objects for traversal.

---

### 2. Object Traversal (Closure Algorithm)

We build a **closure** of all objects needed for a valid snapshot.

#### Always follow (default)

- **Forward ForeignKey** relations
  - Only non-null FK fields are required.
  - Ensures the fixture includes all rows needed for referential integrity.
- **Forward ManyToMany** relations
  - Include related objects plus through-table rows.

#### Optional toggle

- **Reverse ForeignKey** relations (child objects)
- **Reverse ManyToMany** relations

These allow exporting hierarchical data (e.g. Orders + OrderItems).

#### Traversal notes

- Use `_meta.get_fields()` to detect both forward and reverse relations.
- Use `ManyToOneRel` and `ManyToManyRel` to locate reverse relations.
- Maintain a `set((model_label, pk))` of seen objects to avoid duplicates.
- Perform BFS/DFS until traversal completes or hits the object limit.

---

## 3. Object Limit (Safety Cap)

Stop traversal if total collected objects exceed a configurable limit (default: ~5,000).

Warning example:

> "Snapshot exceeded the safety limit. Increase the cap or reduce root objects."

Prevents accidental full-DB exports (especially in prod).

---

## 4. Environment Rules

- **Local/dev:** everything allowed.
- **Staging/QA:** allowed with object limit and PII warning.
- **Prod:** disabled by default unless explicitly enabled via env var.

---

## 5. Serialization

Use Django’s built-in serializer:

```python
from django.core import serializers
data = serializers.serialize(fmt, instances, use_natural_foreign_keys=False)
```

Supported formats:

- JSON (default)
- YAML

Serialize the final deduplicated list of objects.

---

## 6. Admin UI

### Admin Action (per model)

1. User selects rows → chooses **"Export as fixture…"**.
2. Redirect to a configuration screen:
   - Format: JSON / YAML
   - Include reverse relations? (checkbox)
   - Max object cap override?
3. After submission:
   - Show fixture in a read-only textarea
   - Provide a "Download" button
   - Show usage hint: `python manage.py loaddata <file>`

### Snapshot Builder (optional extension)

A global admin view for saving "snapshot specs":

- Multiple root querysets (e.g. all `Plan`, all `FeatureFlag`)
- Include reverse relations or not
- Max depth (optional)
- Max object cap
- Save/load snapshot profiles (e.g. "Minimum demo data")

---

## 7. Loading Guarantees

If using forward FKs plus forward M2Ms closure:

- `loaddata` will not fail due to missing required rows.
- Reverse relations are optional but useful when exporting hierarchies.

---

## 8. Implementation Notes

### Detecting relations

```python
from django.db.models import ForeignKey, ManyToManyField
from django.db.models.fields.reverse_related import ManyToOneRel, ManyToManyRel
```

### Traversal helper (conceptual pseudocode)

```python
queue = deque(initial_objects)
seen = set()

while queue:
    obj = queue.popleft()
    key = (obj._meta.label_lower, obj.pk)
    if key in seen:
        continue
    seen.add(key)

    # Safety cap
    if len(seen) > OBJECT_LIMIT:
        raise TooManyObjects()

    for field in obj._meta.get_fields():

        # Forward FK
        if isinstance(field, ForeignKey):
            target = getattr(obj, field.name, None)
            if target is not None:
                queue.append(target)

        # Forward M2M
        elif isinstance(field, ManyToManyField):
            for target in getattr(obj, field.name).all():
                queue.append(target)

        # Reverse relations (optional)
        if include_reverse:
            # Reverse FK
            if isinstance(field, ManyToOneRel):
                rel_manager = getattr(obj, field.get_accessor_name())
                for target in rel_manager.all():
                    queue.append(target)

            # Reverse M2M
            elif isinstance(field, ManyToManyRel):
                rel_manager = getattr(obj, field.get_accessor_name())
                for target in rel_manager.all():
                    queue.append(target)

# After traversal:
# 'seen' holds all necessary (model, pk) pairs.
# Convert them to model instances and serialize.
```

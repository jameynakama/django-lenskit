from __future__ import annotations

import json
import os
import re
from typing import Any, Dict

from django.apps import apps as django_apps
from django.conf import settings


class LlmNotConfigured(Exception):
    pass


def _ai_cfg() -> Dict[str, Any]:
    cfg = getattr(settings, "ADMIN_LENSKIT", {}) or {}
    ai = cfg.get("ai_query") if isinstance(cfg, dict) else None
    return ai if isinstance(ai, dict) else {}


def _available_model_labels() -> list[str]:
    from django.apps import apps as django_apps

    models = []
    for m in django_apps.get_models():
        models.append(f"{m._meta.app_label}.{m._meta.object_name}")
    # Filter by allowed_models if set to a list
    ai = _ai_cfg()
    allowed = ai.get("allowed_models")
    if isinstance(allowed, list) and "*" not in allowed:
        models = [lbl for lbl in models if lbl in allowed]
    # Keep list manageable
    return sorted(models)[:200]


def is_configured() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def _build_system_prompt(schema_text: str) -> str:
    avail = _available_model_labels()
    example_label = avail[0] if avail else "auth.User"
    return (
        "You are a helpful assistant that converts natural language into a STRICT JSON DSL for Django ORM (read-only).\n"
        "Rules:\n"
        "- Output ONLY a JSON object, no code fences, no commentary.\n"
        "- Keys allowed: model, fields, filters, exclude, order_by, limit.\n"
        "- Use Django lookups with '__', e.g., title__icontains.\n"
        "- Always include 'limit'.\n"
        "- Never include writes, raw SQL, or unknown keys.\n"
        "- The 'model' MUST be one of the following available model labels: "
        + ", ".join(avail)
        + ".\n"
        f"Schema:\n{schema_text}\n"
        "Example output:\n"
        f'{{"model":"{example_label}","fields":["id","name"],"filters":{{"name__icontains":"foo"}},"exclude":{{}},"order_by":["-id"],"limit":50}}'
    )


def _schema_from_settings() -> str:
    ai = _ai_cfg()
    allowed_models = ai.get("allowed_models")
    allowed_fields = ai.get("allowed_fields") or {}
    models_desc = allowed_models if allowed_models else []
    if allowed_models == "*" or (isinstance(allowed_models, list) and "*" in allowed_models):
        models_desc = ["*"]

    # Include per-model fields to guide the model toward real field names, including inherited ones
    def _model_fields_map() -> Dict[str, list[str]]:
        out: Dict[str, list[str]] = {}
        for m in django_apps.get_models():
            label = f"{m._meta.app_label}.{m._meta.object_name}"
            names: list[str] = []
            for f in m._meta.get_fields():
                if getattr(f, "auto_created", False) and not getattr(f, "concrete", False):
                    continue
                if getattr(f, "one_to_many", False) or (
                    getattr(f, "many_to_many", False) and getattr(f, "auto_created", False)
                ):
                    continue
                name = getattr(f, "name", None)
                if name:
                    names.append(name)
            names.append("pk")
            out[label] = sorted(set(names))
        return out

    payload = {
        "allowed_models": models_desc,
        "allowed_fields": allowed_fields,
        "available_models": _available_model_labels(),
        "model_fields": _model_fields_map(),
    }
    return json.dumps(payload, separators=(",", ":"))


def _extract_json(s: str) -> Dict[str, Any]:
    s = s.strip()
    # If the model returns fenced code, try to extract the JSON
    m = re.search(r"\{.*\}", s, flags=re.S | re.M)
    if m:
        candidate = m.group(0)
        try:
            parsed: Dict[str, Any] = json.loads(candidate)
            return parsed
        except Exception:
            pass
    # Fallback to plain parse
    parsed2: Dict[str, Any] = json.loads(s)
    return parsed2


def generate_dsl_from_nl(nl: str) -> Dict[str, Any]:
    if not is_configured():
        raise LlmNotConfigured("OPENAI_API_KEY not set")
    # Late import to avoid hard dependency in environments without the client
    try:
        import importlib

        openai_module = importlib.import_module("openai")
        OpenAI = getattr(openai_module, "OpenAI")
    except Exception as e:  # pragma: no cover - environment-specific
        raise LlmNotConfigured("OpenAI client not available") from e

    client = OpenAI()
    model_name = _ai_cfg().get("openai_model", "gpt-4-1106-preview")
    sys_prompt = _build_system_prompt(_schema_from_settings())
    user_prompt = f"Natural language request:\n{nl}\n\nReturn ONLY the JSON DSL."

    # New Chat Completions API
    resp = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        max_tokens=600,
    )
    content = resp.choices[0].message.content or ""
    return _extract_json(content)

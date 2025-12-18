from __future__ import annotations

import json
import os
import re
from typing import Any, Dict

from django.conf import settings


class LlmNotConfigured(Exception):
    pass


def _ai_cfg() -> Dict[str, Any]:
    cfg = getattr(settings, "ADMIN_LENSKIT", {}) or {}
    ai = cfg.get("ai_query") if isinstance(cfg, dict) else None
    return ai if isinstance(ai, dict) else {}


def is_configured() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def _build_system_prompt(schema_text: str) -> str:
    return (
        "You are a helpful assistant that converts natural language into a STRICT JSON DSL for Django ORM (read-only).\n"
        "Rules:\n"
        "- Output ONLY a JSON object, no code fences, no commentary.\n"
        "- Keys allowed: model, fields, filters, exclude, order_by, limit.\n"
        "- Use Django lookups with '__', e.g., title__icontains.\n"
        "- Always include 'limit'.\n"
        "- Never include writes, raw SQL, or unknown keys.\n"
        f"Schema:\n{schema_text}\n"
        "Example output:\n"
        '{"model":"app.Model","fields":["id","name"],"filters":{"name__icontains":"foo"},"exclude":{},"order_by":["-id"],"limit":50}'
    )


def _schema_from_settings() -> str:
    ai = _ai_cfg()
    allowed_models = ai.get("allowed_models")
    allowed_fields = ai.get("allowed_fields") or {}
    models_desc = allowed_models if allowed_models else []
    if allowed_models == "*" or (isinstance(allowed_models, list) and "*" in allowed_models):
        models_desc = ["*"]
    return json.dumps(
        {"allowed_models": models_desc, "allowed_fields": allowed_fields}, separators=(",", ":")
    )


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

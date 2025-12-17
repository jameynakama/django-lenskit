from __future__ import annotations

import json
from typing import Any, Dict

from django.conf import settings
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from .dsl import DslValidationError, validate_dsl
from .executor import build_queryset, pseudo_code
from .llm import LlmNotConfigured, generate_dsl_from_nl, is_configured


def _ai_cfg() -> dict:
    cfg = getattr(settings, "ADMIN_LENSKIT", {}) or {}
    ai = cfg.get("ai_query") if isinstance(cfg, dict) else None
    return ai if isinstance(ai, dict) else {}


def _enabled() -> bool:
    ai = _ai_cfg()
    if "enabled" in ai:
        return bool(ai["enabled"])
    return bool(getattr(settings, "DEBUG", False))


def _require_superuser() -> bool:
    return bool(_ai_cfg().get("require_superuser", True))


@staff_member_required
def ui(request: HttpRequest) -> HttpResponse:
    if not _enabled():
        return render(request, "admin_lenskit/ai_query.html", {"error": "AI query is disabled."}, status=403)
    if _require_superuser() and not request.user.is_superuser:
        return render(request, "admin_lenskit/ai_query.html", {"error": "Superuser required."}, status=403)

    context: Dict[str, Any] = {"error": None, "dsl_text": "", "orm": "", "rows": [], "allowed_models": _ai_cfg().get("allowed_models", [])}
    if request.method == "POST":
        dsl_text = request.POST.get("dsl") or ""
        context["dsl_text"] = dsl_text
        try:
            dsl_obj = json.loads(dsl_text or "{}")
            model, spec = validate_dsl(dsl_obj)
            qs = build_queryset(model, spec)
            rows = list(qs)
            context["orm"] = pseudo_code(model, spec)
            context["rows"] = rows
        except (json.JSONDecodeError, DslValidationError) as e:
            context["error"] = str(e)
    return render(request, "admin_lenskit/ai_query.html", context)


@csrf_exempt
@staff_member_required
def api(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    if not _enabled():
        return JsonResponse({"error": "AI query is disabled"}, status=403)
    if _require_superuser() and not request.user.is_superuser:
        return JsonResponse({"error": "Superuser required"}, status=403)
    try:
        data = json.loads(request.body.decode("utf-8"))
        model, spec = validate_dsl(data)
        qs = build_queryset(model, spec)
        rows = list(qs)
        return JsonResponse({"dsl": spec, "orm": pseudo_code(model, spec), "rows": rows})
    except (json.JSONDecodeError, DslValidationError) as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
@staff_member_required
def generate_api(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    if not _enabled():
        return JsonResponse({"error": "AI query is disabled"}, status=403)
    if _require_superuser() and not request.user.is_superuser:
        return JsonResponse({"error": "Superuser required"}, status=403)
    data = json.loads(request.body.decode("utf-8")) if request.body else {}
    nl = data.get("query") if isinstance(data, dict) else None
    if not nl or not isinstance(nl, str):
        return JsonResponse({"error": "Missing 'query' string"}, status=400)
    try:
        dsl_obj = generate_dsl_from_nl(nl)
        # Validate before returning
        model, spec = validate_dsl(dsl_obj)
        return JsonResponse({"dsl": spec})
    except LlmNotConfigured as e:
        return JsonResponse({"error": str(e)}, status=501)
    except DslValidationError as e:
        return JsonResponse({"error": f"Invalid DSL: {e}"}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"Generation failed: {e}"}, status=500)

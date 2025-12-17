from __future__ import annotations

from typing import Any

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.contenttypes.models import ContentType
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from .exporter import TooManyObjects, export_queryset, fixtures_enabled
from .forms import FixtureExportForm


def _parse_model(model_label: str):
    try:
        app_label, model_name = model_label.split(".", 1)
    except ValueError:
        return None
    try:
        ct = ContentType.objects.get_by_natural_key(app_label, model_name.lower())
        return ct.model_class()
    except Exception:
        return None


@staff_member_required
def export_config_view(request: HttpRequest) -> HttpResponse:
    if not fixtures_enabled():
        return HttpResponseBadRequest("Fixture export is disabled")

    model_label = request.GET.get("model")
    pks_csv = request.GET.get("pks", "")
    if not model_label:
        return HttpResponseBadRequest("Missing model parameter")

    model = _parse_model(model_label)
    if model is None:
        return HttpResponseBadRequest("Invalid model parameter")

    ids: list[str] = [s.strip() for s in pks_csv.split(",") if s.strip()]
    if not ids:
        return HttpResponseBadRequest("Invalid pks parameter")
    pks: list[Any] = ids

    default_limit = request.GET.get("limit")
    form_initial = {
        "fmt": request.GET.get("fmt") or "json",
        "include_reverse": bool(request.GET.get("rev")),
    }
    if default_limit:
        try:
            form_initial["object_limit"] = int(default_limit)
        except Exception:
            pass

    if request.method == "POST":
        form = FixtureExportForm(request.POST)
        if form.is_valid():
            fmt = form.cleaned_data["fmt"]
            include_reverse = form.cleaned_data["include_reverse"]
            object_limit = form.cleaned_data["object_limit"]
            qs = model._default_manager.filter(pk__in=pks)
            try:
                data = export_queryset(
                    qs,
                    include_reverse=include_reverse,
                    object_limit=object_limit,
                    fmt=fmt,
                )
            except TooManyObjects as e:
                return render(
                    request,
                    "admin_lenskit/fixture_export.html",
                    {
                        "form": form,
                        "model_label": model_label,
                        "pks_csv": pks_csv,
                        "error": str(e),
                        "data": None,
                    },
                )
            response = render(
                request,
                "admin_lenskit/fixture_export.html",
                {
                    "form": form,
                    "model_label": model_label,
                    "pks_csv": pks_csv,
                    "error": None,
                    "data": data,
                },
            )
            if request.POST.get("download"):
                filename = f"{model._meta.model_name}_fixture.{fmt}"
                response = HttpResponse(data, content_type="application/octet-stream")
                response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response
    else:
        form = FixtureExportForm(initial=form_initial)

    return render(
        request,
        "admin_lenskit/fixture_export.html",
        {
            "form": form,
            "model_label": model_label,
            "pks_csv": pks_csv,
            "error": None,
            "data": None,
        },
    )


def export_action(modeladmin, request: HttpRequest, queryset):
    ids = ",".join(str(pk) for pk in queryset.values_list("pk", flat=True))
    model = queryset.model
    label = f"{model._meta.app_label}.{model._meta.model_name}"
    url = reverse("django_lenskit_fixtures:export_config")
    return HttpResponseRedirect(f"{url}?model={label}&pks={ids}")


export_action.short_description = "Export as fixture…"  # type: ignore[attr-defined]

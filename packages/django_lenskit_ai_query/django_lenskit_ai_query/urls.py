from __future__ import annotations

from django.contrib import admin
from django.urls import path

from .views import api, ui, generate_api

app_name = "django_lenskit_ai_query"

urlpatterns = [
    path("ai/", admin.site.admin_view(ui), name="ui"),
    path("ai/api/", admin.site.admin_view(api), name="api"),
    path("ai/generate/", admin.site.admin_view(generate_api), name="generate"),
]

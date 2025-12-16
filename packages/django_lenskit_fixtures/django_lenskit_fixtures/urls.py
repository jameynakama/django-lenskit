from __future__ import annotations

from django.contrib import admin
from django.urls import path

from .views import export_config_view

app_name = "django_lenskit_fixtures"

urlpatterns = [
    path("fixtures/export/", admin.site.admin_view(export_config_view), name="export_config"),
]

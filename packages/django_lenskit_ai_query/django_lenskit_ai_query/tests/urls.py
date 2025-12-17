from __future__ import annotations

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/lenskit/", include("django_lenskit_ai_query.urls")),
    path("admin/", admin.site.urls),
]

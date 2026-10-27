from django.contrib import admin
from django.urls import include, path

from apps.core.views import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health, name="health"),
    path("api/", include("apps.accounts.urls")),
    path("api/", include("apps.tenants.urls")),
    path("api/", include("apps.subscriptions.urls")),
    path("api/", include("apps.academics.urls")),
    path("api/", include("apps.students.urls")),
]

from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import InstituteLookupView, InstituteRegistrationView, TenantViewSet

router = DefaultRouter()
router.register("platform/tenants", TenantViewSet, basename="tenant")

urlpatterns = [
    path("public/institutes/<str:code>/", InstituteLookupView.as_view(), name="institute-lookup"),
    path("public/register/", InstituteRegistrationView.as_view(), name="institute-register"),
    *router.urls,
]

from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ApplicationViewSet, PublicAdmissionView

router = DefaultRouter()
router.register("admissions", ApplicationViewSet, basename="admission")

urlpatterns = [
    path("public/admissions/<str:code>/", PublicAdmissionView.as_view(), name="public-admission"),
    *router.urls,
]

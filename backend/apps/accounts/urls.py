from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import InstituteLoginView, MeView, PlatformLoginView, UserViewSet

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")

urlpatterns = [
    path("auth/login/", InstituteLoginView.as_view(), name="login"),
    path("auth/platform-login/", PlatformLoginView.as_view(), name="platform-login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("auth/me/", MeView.as_view(), name="me"),
    *router.urls,
]

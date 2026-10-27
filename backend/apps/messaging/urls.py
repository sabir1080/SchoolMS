from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import MessageViewSet, MessagingSettingsView, PushView

router = DefaultRouter()
router.register("messages", MessageViewSet, basename="message")

urlpatterns = [
    path("push/", PushView.as_view(), name="push"),
    path("messages/settings/", MessagingSettingsView.as_view(), name="messaging-settings"),
    *router.urls,
]

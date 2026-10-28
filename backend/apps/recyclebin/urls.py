from django.urls import path

from .views import RecycleBinItemView, RecycleBinView

urlpatterns = [
    path("recycle-bin/", RecycleBinView.as_view(), name="recycle-bin"),
    path("recycle-bin/<int:pk>/", RecycleBinItemView.as_view(), name="recycle-bin-item"),
]

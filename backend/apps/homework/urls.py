from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import HomeworkViewSet, MyHomeworkView

router = DefaultRouter()
router.register("homework", HomeworkViewSet, basename="homework")

urlpatterns = [
    path("me/homework/", MyHomeworkView.as_view(), name="my-homework"),
    *router.urls,
]

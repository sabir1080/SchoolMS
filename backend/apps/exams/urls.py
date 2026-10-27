from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ExamViewSet, GradingView, MyExamsView

router = DefaultRouter()
router.register("exams", ExamViewSet, basename="exam")

urlpatterns = [
    path("exams/grading/", GradingView.as_view(), name="exam-grading"),
    path("me/exams/", MyExamsView.as_view(), name="my-exams"),
    *router.urls,
]

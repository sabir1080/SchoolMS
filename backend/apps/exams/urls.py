from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ExamViewSet, GradingView, MarksProgressView, MarksSheetView, MyExamsView

router = DefaultRouter()
router.register("exams", ExamViewSet, basename="exam")

urlpatterns = [
    path("exams/grading/", GradingView.as_view(), name="exam-grading"),
    path("exams/<int:exam_id>/marks/", MarksSheetView.as_view(), name="exam-marks"),
    path("exams/<int:exam_id>/marks/progress/", MarksProgressView.as_view(), name="exam-marks-progress"),
    path("me/exams/", MyExamsView.as_view(), name="my-exams"),
    *router.urls,
]

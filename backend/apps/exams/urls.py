from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CombinedResultsView,
    CombinedResultViewSet,
    ExamViewSet,
    GradingView,
    MarksProgressView,
    MarksSheetView,
    MyExamsView,
    MyResultsView,
    ResultsView,
)

router = DefaultRouter()
router.register("exams", ExamViewSet, basename="exam")
router.register("combined-results", CombinedResultViewSet, basename="combined-result")

urlpatterns = [
    path("exams/grading/", GradingView.as_view(), name="exam-grading"),
    path("exams/<int:exam_id>/marks/", MarksSheetView.as_view(), name="exam-marks"),
    path("exams/<int:exam_id>/marks/progress/", MarksProgressView.as_view(), name="exam-marks-progress"),
    path("exams/<int:exam_id>/results/", ResultsView.as_view(), name="exam-results"),
    path("combined-results/<int:combined_id>/results/", CombinedResultsView.as_view(), name="combined-results-sheet"),
    path("me/results/", MyResultsView.as_view(), name="my-results"),
    path("me/exams/", MyExamsView.as_view(), name="my-exams"),
    *router.urls,
]

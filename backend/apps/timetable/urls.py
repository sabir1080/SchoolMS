from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import EntryViewSet, MyTimetableView, PeriodViewSet

router = DefaultRouter()
router.register("timetable/periods", PeriodViewSet, basename="period")
router.register("timetable/entries", EntryViewSet, basename="timetable-entry")

urlpatterns = [
    path("me/timetable/", MyTimetableView.as_view(), name="my-timetable"),
    *router.urls,
]

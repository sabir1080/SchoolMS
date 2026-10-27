from django.urls import path

from .views import MonthlyReportView, MyAttendanceView, MySectionsView, SheetView, StudentAttendanceView, TodayView

urlpatterns = [
    path("attendance/sections/", MySectionsView.as_view(), name="attendance-sections"),
    path("attendance/sheet/", SheetView.as_view(), name="attendance-sheet"),
    path("attendance/report/", MonthlyReportView.as_view(), name="attendance-report"),
    path("attendance/today/", TodayView.as_view(), name="attendance-today"),
    path("attendance/students/<int:pk>/", StudentAttendanceView.as_view(), name="attendance-student"),
    path("me/attendance/", MyAttendanceView.as_view(), name="my-attendance"),
]

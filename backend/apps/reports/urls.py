from django.urls import path

from .views import ReportView

urlpatterns = [path("reports/<slug:name>/", ReportView.as_view(), name="report")]

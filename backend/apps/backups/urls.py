from django.urls import path

from .views import (
    InstituteBackupStatusView,
    InstituteBackupView,
    InstituteExcelView,
    PlatformSnapshotsView,
    PlatformTenantBackupView,
    PlatformTenantRestoreView,
)

urlpatterns = [
    path("institute/backup/", InstituteBackupView.as_view(), name="institute-backup"),
    path("institute/backup/excel/", InstituteExcelView.as_view(), name="institute-backup-excel"),
    path("institute/backup/status/", InstituteBackupStatusView.as_view(), name="institute-backup-status"),
    path("platform/tenants/<int:pk>/backup/", PlatformTenantBackupView.as_view(), name="platform-tenant-backup"),
    path("platform/tenants/<int:pk>/restore/", PlatformTenantRestoreView.as_view(), name="platform-tenant-restore"),
    path("platform/tenants/<int:pk>/snapshots/", PlatformSnapshotsView.as_view(), name="platform-tenant-snapshots"),
    path("platform/tenants/<int:pk>/snapshots/<int:snapshot_id>/", PlatformSnapshotsView.as_view(), name="platform-tenant-snapshot"),
]

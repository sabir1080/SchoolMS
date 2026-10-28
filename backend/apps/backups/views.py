import os

from django.http import FileResponse, HttpResponse
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsInstituteAdmin, IsSuperAdmin
from apps.tenants.models import Tenant

from . import institute
from .excel import institute_workbook
from .models import BackupRecord, InstituteBackupLog, InstituteSnapshot
from .services import create_backup


class _DeleteOnClose:
    """File wrapper that removes the temporary backup once it has been sent."""

    def __init__(self, path):
        self.path, self.file = path, open(path, "rb")

    def read(self, *args):
        return self.file.read(*args)

    def close(self):
        self.file.close()
        try:
            os.remove(self.path)
        except OSError:
            pass


class BackupDownloadView(APIView):
    """The platform owner downloads a full backup of every institute."""

    permission_classes = [IsSuperAdmin]

    def get(self, request):
        path = create_backup()
        BackupRecord.objects.create(size_bytes=os.path.getsize(path), institutes=Tenant.objects.count(), created_by=request.user)
        name = timezone.localtime().strftime("schoolms-backup-%Y-%m-%d-%H%M.json.gz")
        return FileResponse(_DeleteOnClose(path), as_attachment=True, filename=name, content_type="application/gzip")


def last_backup():
    record = BackupRecord.objects.first()
    if record is None:
        return None
    return {"created_at": record.created_at, "days_ago": (timezone.now() - record.created_at).days,
            "size_bytes": record.size_bytes, "institutes": record.institutes}


# --- One institute -----------------------------------------------------------------------------------------

MAX_UPLOAD = 50 * 1024 * 1024


def _download(content, filename, content_type):
    response = HttpResponse(content, content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def _stamp():
    return timezone.localtime().strftime("%Y-%m-%d-%H%M")


class InstituteBackupView(APIView):
    """An institute admin downloads the institute's own data (works even after the subscription expired)."""

    permission_classes = [IsInstituteAdmin]

    def get(self, request):
        tenant = request.user.tenant
        content = institute.export_file(tenant, include_secrets=False)
        InstituteBackupLog.objects.create(tenant=tenant, kind="file", created_by=request.user)
        return _download(content, f"{tenant.slug}-backup-{_stamp()}.json.gz", "application/gzip")


class InstituteExcelView(APIView):
    permission_classes = [IsInstituteAdmin]

    def get(self, request):
        tenant = request.user.tenant
        content = institute_workbook(tenant)
        InstituteBackupLog.objects.create(tenant=tenant, kind="excel", created_by=request.user)
        return _download(content, f"{tenant.slug}-data-{_stamp()}.xlsx",
                         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


class InstituteBackupStatusView(APIView):
    permission_classes = [IsInstituteAdmin]

    def get(self, request):
        logs = InstituteBackupLog.objects.filter(tenant=request.user.tenant)
        last = {kind: logs.filter(kind=kind).values_list("created_at", flat=True).first() for kind in ("file", "excel")}
        days = (timezone.now() - last["file"]).days if last["file"] else None
        return Response({"last_file": last["file"], "last_excel": last["excel"], "days_since_file": days})


class PlatformTenantBackupView(APIView):
    """The owner downloads one institute's backup (with its payment keys, for a full restore)."""

    permission_classes = [IsSuperAdmin]

    def get(self, request, pk):
        tenant = Tenant.objects.filter(pk=pk).first()
        if tenant is None:
            raise NotFound("Institute not found.")
        content = institute.export_file(tenant, include_secrets=True)
        InstituteBackupLog.objects.create(tenant=tenant, kind="file", created_by=request.user)
        return _download(content, f"{tenant.slug}-backup-{_stamp()}.json.gz", "application/gzip")


class PlatformTenantRestoreView(APIView):
    """Restore one institute from its backup file or from a full backup. Without ``confirm_code`` it only
    describes what would happen; with the institute code typed in, it restores (saving the current data first)."""

    permission_classes = [IsSuperAdmin]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, pk):
        tenant = Tenant.objects.filter(pk=pk).first()
        if tenant is None:
            raise NotFound("Institute not found.")
        upload = request.FILES.get("file")
        if upload is None:
            raise ValidationError({"file": ["Choose a backup file."]})
        if upload.size > MAX_UPLOAD:
            raise ValidationError({"file": ["The file is too large."]})
        try:
            rows, info = institute.read_file(upload.read(), tenant)
        except institute.BackupFileError as exc:
            raise ValidationError({"file": [str(exc)]})
        preview = {**info, "institute": tenant.slug, "name": tenant.name, "backup": institute.summary(rows),
                   "current": institute.current_summary(tenant)}
        code = str(request.data.get("confirm_code", "")).strip().lower()
        if not code:
            return Response({**preview, "restored": False})
        if code != tenant.slug:
            raise ValidationError({"confirm_code": [f"Type the institute code “{tenant.slug}” to confirm."]})
        try:
            safety, counts = institute.restore(tenant, rows, request.user)
        except institute.BackupFileError as exc:
            raise ValidationError({"file": [str(exc)]})
        return Response({**preview, "restored": True, "safety_snapshot": safety.pk, "current": institute.current_summary(tenant)})


class SnapshotSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.username", default=None, read_only=True)

    class Meta:
        model = InstituteSnapshot
        fields = ["id", "reason", "size_bytes", "created_at", "created_by_name"]


class PlatformSnapshotsView(APIView):
    """Copies saved before each restore: list, download, or put back (undo a restore)."""

    permission_classes = [IsSuperAdmin]

    def get(self, request, pk, snapshot_id=None):
        snaps = InstituteSnapshot.objects.filter(tenant_id=pk).select_related("created_by")
        if snapshot_id is None:
            return Response(SnapshotSerializer(snaps, many=True).data)
        snap = snaps.filter(pk=snapshot_id).first()
        if snap is None:
            raise NotFound("Saved copy not found.")
        return _download(bytes(snap.data), f"{snap.tenant.slug}-saved-{snap.created_at:%Y-%m-%d-%H%M}.json.gz", "application/gzip")

    def post(self, request, pk, snapshot_id=None):
        tenant = Tenant.objects.filter(pk=pk).first()
        snap = InstituteSnapshot.objects.filter(tenant_id=pk, pk=snapshot_id).first() if snapshot_id else None
        if tenant is None or snap is None:
            raise NotFound("Saved copy not found.")
        if str(request.data.get("confirm_code", "")).strip().lower() != tenant.slug:
            raise ValidationError({"confirm_code": [f"Type the institute code “{tenant.slug}” to confirm."]})
        rows, _ = institute.read_file(bytes(snap.data), tenant)
        safety, _ = institute.restore(tenant, rows, request.user, reason="before putting back a saved copy")
        return Response({"restored": True, "safety_snapshot": safety.pk, "current": institute.current_summary(tenant)})

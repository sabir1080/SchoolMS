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

from . import auto, institute
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
    """Backup status for the Data backup card; PATCH ``auto_backup`` switches the daily automatic backup on or off."""

    permission_classes = [IsInstituteAdmin]

    def patch(self, request):
        tenant = request.user.tenant
        value = request.data.get("auto_backup")
        if not isinstance(value, bool):
            raise ValidationError({"auto_backup": ["Send true or false."]})
        tenant.auto_backup = value
        tenant.save(update_fields=["auto_backup"])
        if value:
            auto.forget(tenant.pk)
            auto.schedule(tenant.pk)  # today's copy right away
        return self.get(request)

    def get(self, request):
        logs = InstituteBackupLog.objects.filter(tenant=request.user.tenant)
        last = {kind: logs.filter(kind=kind).values_list("created_at", flat=True).first() for kind in ("file", "excel")}
        days = (timezone.now() - last["file"]).days if last["file"] else None
        last_auto = InstituteSnapshot.objects.filter(tenant=request.user.tenant, kind=InstituteSnapshot.AUTO).values_list(
            "created_at", flat=True).first()
        return Response({"last_file": last["file"], "last_excel": last["excel"], "days_since_file": days, "last_auto": last_auto,
                         "auto_backup": request.user.tenant.auto_backup})


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


def _confirm(request, tenant):
    if str(request.data.get("confirm_code", "")).strip().lower() != tenant.slug:
        raise ValidationError({"confirm_code": [f"Type the institute code “{tenant.slug}” to confirm."]})


LOCKED_OUT = "Your own login is not in this backup (it was made before your account), so restoring it would lock you out."


class RestoreView(APIView):
    """Restore one institute from a backup file. Without ``confirm_code`` it only describes what would happen; with
    the institute code typed in, it restores (saving the current data first, so it can be undone).

    The owner may use any file of the institute, including a full platform backup. An institute admin may only use
    a file downloaded from SchoolMS for this institute, unchanged (checked with the file's server signature)."""

    parser_classes = [MultiPartParser, FormParser, JSONParser]
    for_owner = True

    def get_tenant(self, request, pk):
        tenant = Tenant.objects.filter(pk=pk).first() if self.for_owner else request.user.tenant
        if tenant is None:
            raise NotFound("Institute not found.")
        return tenant

    def post(self, request, pk=None):
        tenant = self.get_tenant(request, pk)
        upload = request.FILES.get("file")
        if upload is None:
            raise ValidationError({"file": ["Choose a backup file."]})
        if upload.size > MAX_UPLOAD:
            raise ValidationError({"file": ["The file is too large."]})
        try:
            rows, info = institute.read_file(upload.read(), tenant)
        except institute.BackupFileError as exc:
            raise ValidationError({"file": [str(exc)]})
        if not self.for_owner:
            if not info["signed"]:
                raise ValidationError({"file": ["This file was changed or was not downloaded from SchoolMS for this institute. "
                                                "Use a backup file from Data backup, or ask the SchoolMS team."]})
            if not institute.backup_has_user(rows, request.user):
                raise ValidationError({"file": [LOCKED_OUT]})
        preview = {**info, "institute": tenant.slug, "name": tenant.name, "backup": institute.summary(rows),
                   "current": institute.current_summary(tenant)}
        if not str(request.data.get("confirm_code", "")).strip():
            return Response({**preview, "restored": False})
        _confirm(request, tenant)
        try:
            safety, _ = institute.restore(tenant, rows, request.user)
        except institute.BackupFileError as exc:
            raise ValidationError({"file": [str(exc)]})
        return Response({**preview, "restored": True, "safety_snapshot": safety.pk, "current": institute.current_summary(tenant)})


class PlatformTenantRestoreView(RestoreView):
    permission_classes = [IsSuperAdmin]


class InstituteRestoreView(RestoreView):
    permission_classes = [IsInstituteAdmin]
    for_owner = False


class SnapshotSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.username", default=None, read_only=True)

    class Meta:
        model = InstituteSnapshot
        fields = ["id", "kind", "day", "reason", "size_bytes", "created_at", "created_by_name"]


class SnapshotsView(APIView):
    """Copies saved by the app (daily automatic backups, “Back up now”, and before each restore): list, make one now
    (POST without an id), download, or put back.
    The owner's download keeps payment keys; the institute's download leaves them out."""

    for_owner = True

    def get_tenant(self, request, pk):
        tenant = Tenant.objects.filter(pk=pk).first() if self.for_owner else request.user.tenant
        if tenant is None:
            raise NotFound("Institute not found.")
        return tenant

    def get(self, request, pk=None, snapshot_id=None):
        tenant = self.get_tenant(request, pk)
        snaps = InstituteSnapshot.objects.filter(tenant=tenant).select_related("created_by")
        if snapshot_id is None:
            return Response(SnapshotSerializer(snaps, many=True).data)
        snap = snaps.filter(pk=snapshot_id).first()
        if snap is None:
            raise NotFound("Saved copy not found.")
        data = bytes(snap.data) if self.for_owner else institute.without_secrets(bytes(snap.data), tenant)
        when = timezone.localtime(snap.created_at)
        return _download(data, f"{tenant.slug}-{'daily' if snap.kind == snap.AUTO else 'saved'}-{when:%Y-%m-%d-%H%M}.json.gz",
                         "application/gzip")

    def post(self, request, pk=None, snapshot_id=None):
        tenant = self.get_tenant(request, pk)
        if snapshot_id is None:
            return Response(SnapshotSerializer(institute.manual_backup(tenant, request.user)).data, status=201)
        snap = InstituteSnapshot.objects.filter(tenant=tenant, pk=snapshot_id).first() if snapshot_id else None
        if snap is None:
            raise NotFound("Saved copy not found.")
        _confirm(request, tenant)
        rows, _ = institute.read_file(bytes(snap.data), tenant)
        if not self.for_owner and not institute.backup_has_user(rows, request.user):
            raise ValidationError({"confirm_code": [LOCKED_OUT]})
        safety, _ = institute.restore(tenant, rows, request.user, reason="before putting back a saved copy")
        return Response({"restored": True, "safety_snapshot": safety.pk, "current": institute.current_summary(tenant)})


class PlatformSnapshotsView(SnapshotsView):
    permission_classes = [IsSuperAdmin]


class InstituteSnapshotsView(SnapshotsView):
    permission_classes = [IsInstituteAdmin]
    for_owner = False

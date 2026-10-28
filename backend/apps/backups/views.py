import os

from django.http import FileResponse
from django.utils import timezone
from rest_framework.views import APIView

from apps.core.permissions import IsSuperAdmin
from apps.tenants.models import Tenant

from .models import BackupRecord
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

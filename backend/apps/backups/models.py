from django.conf import settings
from django.db import models


class BackupRecord(models.Model):
    """A full backup the platform owner downloaded (to remind them when the last one is old)."""

    created_at = models.DateTimeField(auto_now_add=True)
    size_bytes = models.PositiveBigIntegerField(default=0)
    institutes = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    class Meta:
        ordering = ["-created_at"]


class InstituteBackupLog(models.Model):
    """When an institute (or the owner for it) downloaded its own backup or Excel copy."""

    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="+")
    kind = models.CharField(max_length=10, choices=[("file", "Backup file"), ("excel", "Excel")])
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    class Meta:
        ordering = ["-created_at"]


class InstituteSnapshot(models.Model):
    """An institute's data saved automatically before a restore, so the restore can be undone."""

    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="+")
    reason = models.CharField(max_length=100)
    data = models.BinaryField()
    size_bytes = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    class Meta:
        ordering = ["-created_at"]

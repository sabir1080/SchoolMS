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

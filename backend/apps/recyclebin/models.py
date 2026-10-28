from django.conf import settings
from django.db import models

from apps.core.models import TenantScopedModel

KEEP_DAYS = 30


class DeletedItem(TenantScopedModel):
    """Something an admin deleted, kept for 30 days with everything that was deleted along with it."""

    kind = models.CharField(max_length=50)
    label = models.CharField(max_length=255)
    rows = models.JSONField(default=list)
    relinks = models.JSONField(default=list, help_text="Links that were cleared by the delete and are put back on restore")
    deleted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    restored_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

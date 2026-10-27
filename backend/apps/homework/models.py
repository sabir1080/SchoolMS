from django.conf import settings
from django.db import models

from apps.core.models import TenantScopedModel


class Homework(TenantScopedModel):
    """A diary entry for a section: homework or a note for one day, optionally with a due date."""

    section = models.ForeignKey("academics.Section", on_delete=models.CASCADE, related_name="homework")
    subject = models.ForeignKey("academics.Subject", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    title = models.CharField(max_length=150)
    details = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    class Meta:
        ordering = ["-date", "-id"]
        verbose_name_plural = "homework"

    def __str__(self):
        return self.title

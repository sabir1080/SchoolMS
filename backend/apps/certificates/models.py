from django.conf import settings
from django.db import models

from apps.core.models import TenantScopedModel


class Kind(models.TextChoices):
    CHARACTER = "character", "Character certificate"
    LEAVING = "leaving", "School leaving certificate"
    BONAFIDE = "bonafide", "Bonafide (enrolment) certificate"


class Certificate(TenantScopedModel):
    """An issued certificate. ``data`` keeps the student's details as they were on the day, so a reprint
    always shows the same text."""

    student = models.ForeignKey("students.Student", on_delete=models.PROTECT, related_name="certificates")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    number = models.PositiveIntegerField()
    issued_on = models.DateField()
    data = models.JSONField(default=dict)
    issued_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    class Meta:
        ordering = ["-issued_on", "-number"]
        constraints = [models.UniqueConstraint(fields=["tenant", "number"], name="unique_certificate_number")]

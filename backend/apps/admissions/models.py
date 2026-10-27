from django.conf import settings
from django.db import models

from apps.core.models import TenantScopedModel
from apps.students.models import Gender, Relation


class Status(models.TextChoices):
    NEW = "new", "New"
    APPROVED = "approved", "Admitted"
    REJECTED = "rejected", "Not admitted"


class Application(TenantScopedModel):
    """An admission request a parent sent from the institute's public form."""

    number = models.PositiveIntegerField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.NEW)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices)
    date_of_birth = models.DateField(null=True, blank=True)
    program = models.ForeignKey("academics.Program", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    previous_school = models.CharField(max_length=150, blank=True)
    address = models.TextField(blank=True)
    guardian_name = models.CharField(max_length=150)
    guardian_relation = models.CharField(max_length=20, choices=Relation.choices, default=Relation.FATHER)
    guardian_phone = models.CharField(max_length=30)
    guardian_email = models.EmailField(blank=True)
    guardian_cnic = models.CharField(max_length=30, blank=True)
    message = models.TextField(blank=True)
    admin_note = models.CharField(max_length=255, blank=True)
    student = models.ForeignKey("students.Student", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["tenant", "number"], name="unique_application_number")]

    @property
    def full_name(self):
        return " ".join(filter(None, [self.first_name, self.last_name]))

"""Academic structure shared by every institute type.

The same tables cover a school (Class 5 / Section A), a university (BS Computer Science /
Semester 1-A), a coaching centre (MDCAT Prep / Morning Batch) and a tuition centre. Each
institute can rename "Program" and "Section" in its settings.
"""

from django.conf import settings
from django.db import models, transaction

from apps.core.models import TenantScopedModel


class AcademicSession(TenantScopedModel):
    """An academic year or term, e.g. "2026-27" or "Spring 2027"."""

    name = models.CharField(max_length=50)
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    class Meta:
        ordering = ["-start_date"]
        constraints = [
            models.UniqueConstraint(fields=["tenant", "name"], name="unique_session_name"),
            models.UniqueConstraint(
                fields=["tenant"], condition=models.Q(is_current=True), name="one_current_session"
            ),
            models.CheckConstraint(condition=models.Q(end_date__gt=models.F("start_date")), name="session_end_after_start"),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.is_current:
                AcademicSession.objects.filter(tenant=self.tenant, is_current=True).exclude(pk=self.pk).update(
                    is_current=False
                )
            super().save(*args, **kwargs)


class Subject(TenantScopedModel):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["tenant", "name"], name="unique_subject_name")]

    def __str__(self):
        return self.name


class Program(TenantScopedModel):
    """A class, grade, course or degree program, e.g. "Class 5" or "BS Computer Science"."""

    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, blank=True)
    description = models.CharField(max_length=255, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    subjects = models.ManyToManyField(Subject, blank=True, related_name="programs")

    class Meta:
        ordering = ["sort_order", "name"]
        constraints = [models.UniqueConstraint(fields=["tenant", "name"], name="unique_program_name")]

    def __str__(self):
        return self.name


class Section(TenantScopedModel):
    """A group of students in a program for one session: a section, batch or semester group."""

    program = models.ForeignKey(Program, on_delete=models.PROTECT, related_name="sections")
    session = models.ForeignKey(AcademicSession, on_delete=models.PROTECT, related_name="sections")
    name = models.CharField(max_length=50)
    capacity = models.PositiveIntegerField(null=True, blank=True)
    class_teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["program__sort_order", "program__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["program", "session", "name"], name="unique_section_per_program_session"),
        ]

    def __str__(self):
        return f"{self.program} - {self.name}"

from decimal import Decimal

from django.db import models

from apps.core.models import TenantScopedModel


class GradeBand(TenantScopedModel):
    """One step of an institute's grading scale, e.g. A+ from 90%."""

    name = models.CharField(max_length=20)
    min_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    remark = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ["-min_percentage"]
        constraints = [models.UniqueConstraint(fields=["tenant", "name"], name="unique_grade_name")]


DEFAULT_GRADES = [
    ("A+", 90, "Outstanding"),
    ("A", 80, "Excellent"),
    ("B", 70, "Very good"),
    ("C", 60, "Good"),
    ("D", 50, "Fair"),
    ("E", 33, "Satisfactory"),
    ("F", 0, "Needs improvement"),
]


def grading_scale(tenant):
    """The institute's grade bands (highest first), creating the default scale the first time."""
    bands = list(GradeBand.objects.filter(tenant=tenant))
    if not bands:
        GradeBand.objects.bulk_create(
            [GradeBand(tenant=tenant, name=n, min_percentage=Decimal(p), remark=r) for n, p, r in DEFAULT_GRADES]
        )
        bands = list(GradeBand.objects.filter(tenant=tenant))
    return bands


def grade_for(percentage, bands):
    for band in bands:
        if percentage >= band.min_percentage:
            return band
    return bands[-1] if bands else None


class ExamType(models.TextChoices):
    TEST = "test", "Test"
    TERM = "term", "Term exam"
    MIDTERM = "midterm", "Mid-term"
    FINAL = "final", "Final exam"
    OTHER = "other", "Other"


class ExamStatus(models.TextChoices):
    DRAFT = "draft", "Being prepared"
    MARKS_OPEN = "marks_open", "Marks entry open"
    PUBLISHED = "published", "Result published"


class Exam(TenantScopedModel):
    """An exam in a session (e.g. First Term), taken by some programs (classes)."""

    session = models.ForeignKey("academics.AcademicSession", on_delete=models.PROTECT, related_name="exams")
    name = models.CharField(max_length=100)
    exam_type = models.CharField(max_length=10, choices=ExamType.choices, default=ExamType.TERM)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=ExamStatus.choices, default=ExamStatus.DRAFT)
    programs = models.ManyToManyField("academics.Program", related_name="exams")
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-start_date", "-created_at"]
        constraints = [models.UniqueConstraint(fields=["session", "name"], name="unique_exam_name_per_session")]

    def __str__(self):
        return self.name


class ExamSubject(TenantScopedModel):
    """A paper: one subject of one program in an exam, with its marks and date."""

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="papers")
    program = models.ForeignKey("academics.Program", on_delete=models.CASCADE, related_name="+")
    subject = models.ForeignKey("academics.Subject", on_delete=models.PROTECT, related_name="+")
    total_marks = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal(100))
    pass_marks = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal(33))
    date = models.DateField(null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)

    class Meta:
        # Papers without a date go last in the date sheet.
        ordering = [models.F("date").asc(nulls_last=True), models.F("start_time").asc(nulls_last=True), "subject__name"]
        constraints = [
            models.UniqueConstraint(fields=["exam", "program", "subject"], name="unique_paper"),
        ]

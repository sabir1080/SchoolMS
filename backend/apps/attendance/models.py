from django.conf import settings
from django.db import models

from apps.core.models import TenantScopedModel


class AttendanceStatus(models.TextChoices):
    PRESENT = "present", "Present"
    ABSENT = "absent", "Absent"
    LEAVE = "leave", "Leave"
    LATE = "late", "Late"


# Statuses that count as attending when working out the attendance percentage.
ATTENDED = (AttendanceStatus.PRESENT, AttendanceStatus.LATE)


class AttendanceRecord(TenantScopedModel):
    """One student's daily attendance in their section."""

    # PROTECT: a student or section with attendance history is marked inactive, not deleted.
    student = models.ForeignKey("students.Student", on_delete=models.PROTECT, related_name="attendance")
    section = models.ForeignKey("academics.Section", on_delete=models.PROTECT, related_name="attendance")
    date = models.DateField()
    status = models.CharField(max_length=10, choices=AttendanceStatus.choices)
    remark = models.CharField(max_length=200, blank=True)
    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        ordering = ["date"]
        constraints = [models.UniqueConstraint(fields=["student", "date"], name="one_attendance_per_student_day")]
        indexes = [models.Index(fields=["section", "date"])]


def summarize(statuses):
    """Counts per status and the attendance percentage for an iterable of status strings.

    Leave days are left out of the percentage: (present + late) / (days - leave days).
    """
    counts = {s: 0 for s in AttendanceStatus.values}
    for status in statuses:
        counts[status] += 1
    total = sum(counts.values())
    attended = sum(counts[s] for s in ATTENDED)
    counted = total - counts[AttendanceStatus.LEAVE]
    return {**counts, "total": total, "percentage": round(attended * 100 / counted, 1) if counted else None}

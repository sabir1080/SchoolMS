from django.conf import settings
from django.db import models

from apps.core.models import TenantScopedModel

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


class Period(TenantScopedModel):
    """A slot of the school day (the bell schedule), e.g. "Period 1" 08:00-08:40 or a break."""

    name = models.CharField(max_length=40)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_break = models.BooleanField(default=False)

    class Meta:
        ordering = ["start_time", "id"]

    def __str__(self):
        return self.name


class TimetableEntry(TenantScopedModel):
    """What a section studies in one period of one weekday, and who teaches it."""

    section = models.ForeignKey("academics.Section", on_delete=models.CASCADE, related_name="timetable")
    day = models.PositiveSmallIntegerField()  # 0 = Monday ... 6 = Sunday
    period = models.ForeignKey(Period, on_delete=models.CASCADE, related_name="entries")
    subject = models.ForeignKey("academics.Subject", on_delete=models.CASCADE, null=True, blank=True, related_name="+")
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="timetable_entries"
    )
    room = models.CharField(max_length=30, blank=True)

    class Meta:
        ordering = ["day", "period__start_time"]
        constraints = [
            models.UniqueConstraint(fields=["section", "day", "period"], name="one_entry_per_section_slot"),
        ]

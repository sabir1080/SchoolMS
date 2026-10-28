from django.db import models

from apps.core.models import TimeStampedModel

from apps.accounts.passwords import PasswordPolicy

from .validators import validate_institute_code


class InstituteType(models.TextChoices):
    SCHOOL = "school", "School"
    COLLEGE = "college", "College"
    UNIVERSITY = "university", "University"
    COACHING = "coaching", "Coaching Center"
    TUITION = "tuition", "Tuition Center"


class Tenant(TimeStampedModel):
    """An institute using the platform. All institute data hangs off a tenant."""

    name = models.CharField(max_length=200)
    # The "institute code" users type on the login screen.
    slug = models.SlugField(max_length=30, unique=True, validators=[validate_institute_code])
    institute_type = models.CharField(max_length=20, choices=InstituteType.choices)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    country = models.CharField(max_length=2, default="PK", help_text="ISO 3166-1 alpha-2 code")
    currency = models.CharField(max_length=3, default="PKR", help_text="ISO 4217 code")
    timezone = models.CharField(max_length=50, default="Asia/Karachi")
    is_active = models.BooleanField(default=True)
    # What this institute calls a Program and a Section, e.g. "Class"/"Section" or "Course"/"Batch".
    # Blank means the default for the institute type.
    program_label = models.CharField(max_length=30, blank=True)
    section_label = models.CharField(max_length=30, blank=True)
    # Exams: a subject is passed at this percentage; show class position on report cards.
    pass_percentage = models.PositiveSmallIntegerField(default=33)
    show_position = models.BooleanField(default=True)
    # School days for the timetable, as weekday numbers (0 = Monday): Monday to Friday by default.
    working_days = models.CharField(max_length=20, default="0,1,2,3,4")
    # Branding (plan feature "white_label"): a small logo kept as a data URL, and a theme colour key.
    logo = models.TextField(blank=True)
    admissions_open = models.BooleanField(default=False, help_text="Parents can send applications from the online form")
    auto_backup = models.BooleanField(default=True, help_text="Save a copy of the data automatically every day the app is used")
    brand_color = models.CharField(max_length=20, default="indigo")
    password_policy = models.CharField(
        max_length=10, choices=PasswordPolicy.choices, default=PasswordPolicy.EASY
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

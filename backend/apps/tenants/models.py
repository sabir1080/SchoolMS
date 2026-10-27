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
    password_policy = models.CharField(
        max_length=10, choices=PasswordPolicy.choices, default=PasswordPolicy.EASY
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

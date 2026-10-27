from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import TenantScopedModel


class Gender(models.TextChoices):
    MALE = "male", "Male"
    FEMALE = "female", "Female"
    OTHER = "other", "Other"


class StudentStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    LEFT = "left", "Left"
    GRADUATED = "graduated", "Graduated"
    SUSPENDED = "suspended", "Suspended"


class Relation(models.TextChoices):
    FATHER = "father", "Father"
    MOTHER = "mother", "Mother"
    GUARDIAN = "guardian", "Guardian"
    BROTHER = "brother", "Brother"
    SISTER = "sister", "Sister"
    OTHER = "other", "Other"


class Guardian(TenantScopedModel):
    """A parent or guardian. One guardian can be linked to several students (siblings)."""

    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30, blank=True)
    cnic = models.CharField("CNIC / ID number", max_length=30, blank=True)
    email = models.EmailField(blank=True)
    occupation = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="guardian_profile"
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Student(TenantScopedModel):
    admission_no = models.CharField(max_length=30)
    # Set when the admission number was generated automatically; used to find the next one.
    admission_seq = models.PositiveIntegerField(null=True, blank=True, editable=False)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices)
    date_of_birth = models.DateField(null=True, blank=True)
    id_number = models.CharField("B-Form / CNIC / ID number", max_length=30, blank=True)
    blood_group = models.CharField(max_length=5, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    admission_date = models.DateField(default=timezone.localdate)
    previous_school = models.CharField(max_length=150, blank=True)
    status = models.CharField(max_length=20, choices=StudentStatus.choices, default=StudentStatus.ACTIVE)
    notes = models.TextField(blank=True)
    guardians = models.ManyToManyField(Guardian, through="StudentGuardian", related_name="students")
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="student_profile"
    )

    class Meta:
        ordering = ["first_name", "last_name"]
        constraints = [
            models.UniqueConstraint(fields=["tenant", "admission_no"], name="unique_admission_no"),
        ]

    def __str__(self):
        return self.full_name

    @property
    def full_name(self):
        return " ".join(filter(None, [self.first_name, self.last_name]))


class StudentGuardian(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="guardian_links")
    guardian = models.ForeignKey(Guardian, on_delete=models.CASCADE, related_name="student_links")
    relation = models.CharField(max_length=20, choices=Relation.choices, default=Relation.FATHER)
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_primary", "id"]
        constraints = [models.UniqueConstraint(fields=["student", "guardian"], name="unique_student_guardian")]


class Enrollment(TenantScopedModel):
    """A student's place in a section (class/batch) for one academic session."""

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="enrollments")
    section = models.ForeignKey("academics.Section", on_delete=models.PROTECT, related_name="enrollments")
    session = models.ForeignKey("academics.AcademicSession", on_delete=models.PROTECT, related_name="enrollments")
    roll_number = models.CharField(max_length=20, blank=True)
    enrolled_on = models.DateField(default=timezone.localdate)

    class Meta:
        ordering = ["-session__start_date"]
        constraints = [
            models.UniqueConstraint(fields=["student", "session"], name="one_enrollment_per_session"),
            models.UniqueConstraint(
                fields=["section", "roll_number"], condition=~models.Q(roll_number=""), name="unique_roll_in_section"
            ),
        ]

    def save(self, *args, **kwargs):
        self.session_id = self.section.session_id
        super().save(*args, **kwargs)

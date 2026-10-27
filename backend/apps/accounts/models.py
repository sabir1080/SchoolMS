from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.db import models


class Role(models.TextChoices):
    SUPER_ADMIN = "super_admin", "Super Admin"
    ADMIN = "admin", "Institute Admin"
    TEACHER = "teacher", "Teacher"
    STUDENT = "student", "Student"
    PARENT = "parent", "Parent"


class UserManager(DjangoUserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", Role.SUPER_ADMIN)
        extra_fields["tenant"] = None
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    """A person who can log in.

    Super admins run the platform and have no tenant. Every other role belongs
    to exactly one institute (tenant).
    """

    role = models.CharField(max_length=20, choices=Role.choices)
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="users",
    )
    phone = models.CharField(max_length=30, blank=True)

    objects = UserManager()

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="tenant_matches_role",
                condition=(
                    models.Q(role=Role.SUPER_ADMIN, tenant__isnull=True)
                    | (~models.Q(role=Role.SUPER_ADMIN) & models.Q(tenant__isnull=False))
                ),
            ),
            models.UniqueConstraint(
                fields=["email"],
                condition=~models.Q(email=""),
                name="unique_email_when_set",
            ),
        ]

    @property
    def is_super_admin(self):
        return self.role == Role.SUPER_ADMIN

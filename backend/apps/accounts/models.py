from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models


class Role(models.TextChoices):
    SUPER_ADMIN = "super_admin", "Super Admin"
    ADMIN = "admin", "Institute Admin"
    TEACHER = "teacher", "Teacher"
    STUDENT = "student", "Student"
    PARENT = "parent", "Parent"


STAFF_ROLES = (Role.ADMIN, Role.TEACHER)


class UserManager(DjangoUserManager):
    def get_by_natural_key(self, username):
        # Natural keys (createsuperuser, Django admin) only address platform super admins;
        # institute users are looked up together with their institute.
        return self.get(username=username, tenant__isnull=True)

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", Role.SUPER_ADMIN)
        extra_fields["tenant"] = None
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    """A person who can log in.

    Super admins run the platform and have no tenant. Every other role belongs
    to exactly one institute (tenant). Usernames and emails are unique within an
    institute, so two institutes can both have a user called "ali".
    """

    username = models.CharField(
        max_length=150,
        validators=[UnicodeUsernameValidator()],
        help_text="Letters, digits and @/./+/-/_ only. Unique within the institute.",
    )
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
                fields=["tenant", "username"],
                name="unique_username_per_tenant",
            ),
            models.UniqueConstraint(
                fields=["username"],
                condition=models.Q(tenant__isnull=True),
                name="unique_platform_username",
            ),
            models.UniqueConstraint(
                fields=["tenant", "email"],
                condition=~models.Q(email=""),
                name="unique_email_per_tenant",
            ),
        ]

    @property
    def is_super_admin(self):
        return self.role == Role.SUPER_ADMIN

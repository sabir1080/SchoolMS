from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from apps.accounts.models import Role, User
from apps.accounts.passwords import PasswordPolicy, check_password
from apps.subscriptions.serializers import SubscriptionSerializer

from .models import Tenant
from .validators import normalize_code, validate_institute_code


class InstituteCodeField(serializers.CharField):
    """Institute code, lower-cased and trimmed before it is validated."""

    def to_internal_value(self, data):
        return normalize_code(super().to_internal_value(data))


class TenantSerializer(serializers.ModelSerializer):
    subscription = SubscriptionSerializer(read_only=True)
    admin_usernames = serializers.SerializerMethodField()
    slug = InstituteCodeField(
        max_length=30,
        validators=[
            validate_institute_code,
            UniqueValidator(queryset=Tenant.objects.all(), message="This institute code is already taken."),
        ],
    )

    class Meta:
        model = Tenant
        fields = [
            "id", "name", "slug", "institute_type", "email", "phone", "address",
            "country", "currency", "timezone", "password_policy", "is_active", "created_at",
            "subscription", "admin_usernames",
        ]
        read_only_fields = ["id", "created_at"]

    def get_admin_usernames(self, tenant):
        return [u.username for u in tenant.users.all() if u.role == Role.ADMIN]

    def validate_country(self, value):
        return value.upper()

    def validate_currency(self, value):
        return value.upper()


class InstituteRegistrationSerializer(TenantSerializer):
    """Create an institute together with its first admin account (and free trial)."""

    admin_username = serializers.CharField(write_only=True, max_length=150)
    admin_email = serializers.EmailField(write_only=True)
    admin_password = serializers.CharField(write_only=True, style={"input_type": "password"}, trim_whitespace=False)
    admin_first_name = serializers.CharField(write_only=True, required=False, allow_blank=True, default="", max_length=150)
    admin_last_name = serializers.CharField(write_only=True, required=False, allow_blank=True, default="", max_length=150)

    class Meta(TenantSerializer.Meta):
        fields = TenantSerializer.Meta.fields + [
            "admin_username", "admin_email", "admin_password", "admin_first_name", "admin_last_name",
        ]

    def validate_admin_username(self, value):
        return value.strip()

    def validate_admin_email(self, value):
        return value.strip().lower()

    def validate(self, attrs):
        candidate = User(username=attrs["admin_username"], email=attrs["admin_email"])
        policy = attrs.get("password_policy", PasswordPolicy.EASY)
        check_password(attrs["admin_password"], policy, "admin_password", user=candidate)
        return attrs

    def split(self):
        """Return (tenant_fields, admin_fields) from the validated data."""
        data = dict(self.validated_data)
        admin = {key.removeprefix("admin_"): data.pop(key) for key in list(data) if key.startswith("admin_")}
        return data, admin


class PublicInstituteSerializer(serializers.ModelSerializer):
    """What the login screen may show about an institute before anyone logs in."""

    class Meta:
        model = Tenant
        fields = ["name", "slug", "institute_type"]


class InstituteSettingsSerializer(serializers.ModelSerializer):
    """What an institute admin may change about their own institute."""

    class Meta:
        model = Tenant
        fields = [
            "name", "slug", "institute_type", "email", "phone", "address",
            "country", "currency", "timezone", "password_policy", "program_label", "section_label",
        ]
        read_only_fields = ["slug", "institute_type", "country", "currency", "timezone"]


class ResetAdminPasswordSerializer(serializers.Serializer):
    username = serializers.CharField()
    new_password = serializers.CharField(trim_whitespace=False)

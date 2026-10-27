from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from apps.accounts.serializers import check_password_strength
from apps.subscriptions.serializers import SubscriptionSerializer

from .models import Tenant
from .validators import normalize_code, validate_institute_code


class InstituteCodeField(serializers.CharField):
    """Institute code, lower-cased and trimmed before it is validated."""

    def to_internal_value(self, data):
        return normalize_code(super().to_internal_value(data))


class TenantSerializer(serializers.ModelSerializer):
    subscription = SubscriptionSerializer(read_only=True)
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
            "country", "currency", "timezone", "is_active", "created_at", "subscription",
        ]
        read_only_fields = ["id", "created_at"]

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
        check_password_strength(
            attrs["admin_password"],
            {"username": attrs["admin_username"], "email": attrs["admin_email"]},
            "admin_password",
        )
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

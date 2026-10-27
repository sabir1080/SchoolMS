from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from apps.accounts.models import Role, User

from .models import Tenant


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = [
            "id", "name", "slug", "institute_type", "email", "phone", "address",
            "country", "currency", "timezone", "is_active", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class TenantCreateSerializer(TenantSerializer):
    """Create an institute together with its first admin account."""

    admin_username = serializers.CharField(write_only=True)
    admin_email = serializers.EmailField(write_only=True)
    admin_password = serializers.CharField(write_only=True, style={"input_type": "password"})
    admin_first_name = serializers.CharField(write_only=True, required=False, default="")
    admin_last_name = serializers.CharField(write_only=True, required=False, default="")

    class Meta(TenantSerializer.Meta):
        fields = TenantSerializer.Meta.fields + [
            "admin_username", "admin_email", "admin_password", "admin_first_name", "admin_last_name",
        ]

    def validate_admin_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value

    def validate_admin_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate(self, attrs):
        candidate = User(username=attrs["admin_username"], email=attrs["admin_email"])
        try:
            validate_password(attrs["admin_password"], candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"admin_password": list(exc.messages)})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        admin_fields = {
            key.removeprefix("admin_"): validated_data.pop(key)
            for key in list(validated_data)
            if key.startswith("admin_")
        }
        tenant = Tenant.objects.create(**validated_data)
        password = admin_fields.pop("password")
        User.objects.create_user(**admin_fields, password=password, role=Role.ADMIN, tenant=tenant)
        return tenant

from django.contrib.auth import authenticate
from django.contrib.auth.models import update_last_login
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken

from apps.tenants.models import Tenant
from apps.tenants.validators import normalize_code

from .models import Role, User

INVALID_LOGIN = "Incorrect username or password."


def issue_tokens(user):
    """Return access/refresh tokens and the profile for a logged-in user."""
    refresh = RefreshToken.for_user(user)
    refresh["role"] = user.role
    refresh["tenant"] = user.tenant.slug if user.tenant_id else None
    update_last_login(None, user)
    return {"access": str(refresh.access_token), "refresh": str(refresh), "user": MeSerializer(user).data}


def check_password_strength(password, user_fields, field_name):
    try:
        validate_password(password, User(**user_fields))
    except DjangoValidationError as exc:
        raise serializers.ValidationError({field_name: list(exc.messages)})


class InstituteLoginSerializer(serializers.Serializer):
    """Log in to one institute with its code plus username (or email) and password."""

    institute_code = serializers.CharField()
    username = serializers.CharField()
    password = serializers.CharField(style={"input_type": "password"}, trim_whitespace=False)

    def validate(self, attrs):
        tenant = Tenant.objects.filter(slug=normalize_code(attrs["institute_code"])).first()
        if tenant is None:
            raise AuthenticationFailed("Institute code not found.", code="institute_not_found")
        if not tenant.is_active:
            raise AuthenticationFailed("This institute account is suspended.", code="tenant_inactive")
        user = authenticate(
            self.context.get("request"),
            username=attrs["username"].strip(),
            password=attrs["password"],
            tenant=tenant,
        )
        if user is None:
            raise AuthenticationFailed(INVALID_LOGIN, code="invalid_credentials")
        return issue_tokens(user)


class PlatformLoginSerializer(serializers.Serializer):
    """Log in as a platform super admin (no institute code)."""

    username = serializers.CharField()
    password = serializers.CharField(style={"input_type": "password"}, trim_whitespace=False)

    def validate(self, attrs):
        user = authenticate(
            self.context.get("request"), username=attrs["username"].strip(), password=attrs["password"], tenant=None
        )
        if user is None or user.role != Role.SUPER_ADMIN:
            raise AuthenticationFailed(INVALID_LOGIN, code="invalid_credentials")
        return issue_tokens(user)


class TenantSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ["id", "name", "slug", "institute_type", "country", "currency", "timezone"]


class MeSerializer(serializers.ModelSerializer):
    tenant = TenantSummarySerializer(read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "phone", "role", "tenant"]
        read_only_fields = fields


class UserSerializer(serializers.ModelSerializer):
    """Used by institute admins to manage the people in their institute."""

    password = serializers.CharField(
        write_only=True, required=False, style={"input_type": "password"}, trim_whitespace=False
    )
    role = serializers.ChoiceField(choices=[c for c in Role.choices if c[0] != Role.SUPER_ADMIN])

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name", "phone",
            "role", "is_active", "password", "date_joined",
        ]
        read_only_fields = ["id", "date_joined"]

    @property
    def tenant(self):
        return self.context["request"].user.tenant

    def _others(self):
        users = User.objects.filter(tenant=self.tenant)
        return users.exclude(pk=self.instance.pk) if self.instance else users

    def validate_username(self, value):
        value = value.strip()
        if self._others().filter(username=value).exists():
            raise serializers.ValidationError("This username is already used in your institute.")
        return value

    def validate_email(self, value):
        value = value.strip().lower()
        if value and self._others().filter(email__iexact=value).exists():
            raise serializers.ValidationError("This email is already used in your institute.")
        return value

    def validate(self, attrs):
        if self.instance is None and not attrs.get("password"):
            raise serializers.ValidationError({"password": "This field is required."})
        if attrs.get("password"):
            check_password_strength(attrs["password"], {k: v for k, v in attrs.items() if k != "password"}, "password")
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance

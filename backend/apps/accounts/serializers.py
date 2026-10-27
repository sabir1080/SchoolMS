from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.tenants.models import Tenant

from .models import Role, User


class LoginSerializer(TokenObtainPairSerializer):
    """Log in with username or email. Adds role and tenant to the token."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["tenant"] = user.tenant.slug if user.tenant_id else None
        return token

    def validate(self, attrs):
        login = attrs.get(self.username_field, "")
        if "@" in login:
            user = User.objects.filter(email__iexact=login).only("username").first()
            if user:
                attrs[self.username_field] = user.username
        data = super().validate(attrs)
        if self.user.tenant_id and not self.user.tenant.is_active:
            raise AuthenticationFailed("This institute account is suspended.", code="tenant_inactive")
        data["user"] = MeSerializer(self.user).data
        return data


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

    password = serializers.CharField(write_only=True, required=False, style={"input_type": "password"})
    role = serializers.ChoiceField(choices=[c for c in Role.choices if c[0] != Role.SUPER_ADMIN])

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name", "phone",
            "role", "is_active", "password", "date_joined",
        ]
        read_only_fields = ["id", "date_joined"]

    def validate_email(self, value):
        value = value.strip().lower()
        if value and User.objects.filter(email__iexact=value).exclude(pk=getattr(self.instance, "pk", None)).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate(self, attrs):
        if self.instance is None and not attrs.get("password"):
            raise serializers.ValidationError({"password": "This field is required."})
        if attrs.get("password"):
            candidate = User(**{k: v for k, v in attrs.items() if k != "password"})
            try:
                validate_password(attrs["password"], candidate)
            except DjangoValidationError as exc:
                raise serializers.ValidationError({"password": list(exc.messages)})
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

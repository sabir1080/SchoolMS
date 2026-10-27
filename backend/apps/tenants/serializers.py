from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from apps.accounts.models import Role, User
from apps.accounts.passwords import PasswordPolicy, check_password
from apps.subscriptions.serializers import SubscriptionSerializer

from .branding import BRAND_COLORS, LOGO_MAX_CHARS, LOGO_PATTERN, branding_allowed, effective_branding
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


class BrandingFieldsMixin(serializers.Serializer):
    """Read-only branding as it applies now (defaults when the plan lacks white-labeling)."""

    brand = serializers.SerializerMethodField()

    def get_brand(self, tenant):
        logo, key, color = effective_branding(tenant)
        return {"logo": logo, "color": key, "hex": color, "allowed": branding_allowed(tenant)}


class PublicInstituteSerializer(BrandingFieldsMixin, serializers.ModelSerializer):
    """What the login screen may show about an institute before anyone logs in (with its logo and colour)."""

    class Meta:
        model = Tenant
        fields = ["name", "slug", "institute_type", "brand", "admissions_open"]

    def to_representation(self, tenant):
        from apps.admissions.rules import admissions_open

        return {**super().to_representation(tenant), "admissions_open": admissions_open(tenant)}


class InstituteSettingsSerializer(BrandingFieldsMixin, serializers.ModelSerializer):
    """What an institute admin may change about their own institute."""

    logo = serializers.CharField(required=False, allow_blank=True, write_only=True, trim_whitespace=False)
    brand_color = serializers.ChoiceField(choices=list(BRAND_COLORS), required=False, write_only=True)

    class Meta:
        model = Tenant
        fields = [
            "name", "slug", "institute_type", "email", "phone", "address",
            "country", "currency", "timezone", "password_policy", "program_label", "section_label",
            "pass_percentage", "show_position", "working_days", "logo", "brand_color", "brand", "admissions_open",
        ]
        read_only_fields = ["slug", "institute_type", "country", "currency", "timezone"]
        extra_kwargs = {"pass_percentage": {"min_value": 1, "max_value": 100}}

    def validate_logo(self, value):
        if value and (len(value) > LOGO_MAX_CHARS or not LOGO_PATTERN.match(value)):
            raise serializers.ValidationError("Use a PNG, JPG or WebP image under 150 KB.")
        return value

    def validate(self, attrs):
        if ("logo" in attrs or "brand_color" in attrs) and not branding_allowed(self.instance):
            raise serializers.ValidationError("Your plan does not include a logo and theme colour. Upgrade to Pro or Enterprise.")
        return attrs

    def validate_working_days(self, value):
        days = sorted({d.strip() for d in value.split(",") if d.strip()})
        if not days or any(d not in "0123456" or len(d) != 1 for d in days):
            raise serializers.ValidationError("Choose at least one day.")
        return ",".join(days)


class ResetAdminPasswordSerializer(serializers.Serializer):
    username = serializers.CharField()
    new_password = serializers.CharField(trim_whitespace=False)

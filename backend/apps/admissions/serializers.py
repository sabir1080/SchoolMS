from rest_framework import serializers

from apps.academics.models import Program
from apps.messaging.services import normalize_phone

from .models import Application


class ApplicationSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    program_name = serializers.CharField(source="program.name", read_only=True, default=None)
    full_name = serializers.CharField(read_only=True)
    decided_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = [
            "id", "number", "status", "status_label", "full_name", "first_name", "last_name", "gender", "date_of_birth",
            "program", "program_name", "previous_school", "address", "guardian_name", "guardian_relation",
            "guardian_phone", "guardian_email", "guardian_cnic", "message", "admin_note", "student", "created_at",
            "decided_at", "decided_by_name",
        ]
        read_only_fields = [f for f in fields if f != "admin_note"]

    def get_decided_by_name(self, app):
        user = app.decided_by
        return (user.get_full_name() or user.username) if user else None


class PublicApplicationSerializer(serializers.ModelSerializer):
    """What a parent fills in. ``website`` is a hidden field: bots fill it, people do not."""

    program = serializers.PrimaryKeyRelatedField(queryset=Program.objects.none(), required=False, allow_null=True)
    website = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = Application
        fields = [
            "first_name", "last_name", "gender", "date_of_birth", "program", "previous_school", "address",
            "guardian_name", "guardian_relation", "guardian_phone", "guardian_email", "guardian_cnic", "message", "website",
        ]
        extra_kwargs = {"message": {"max_length": 1000}, "address": {"max_length": 500}}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        tenant = self.context["tenant"]
        self.fields["program"].queryset = Program.objects.filter(tenant=tenant, is_active=True)

    def validate_first_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Please enter the student's name.")
        return value

    def validate_guardian_phone(self, value):
        if not normalize_phone(value, self.context["tenant"].country):
            raise serializers.ValidationError("Please enter a valid mobile number, e.g. 0300-1234567.")
        return value.strip()

    def validate(self, attrs):
        if attrs.pop("website", ""):
            raise serializers.ValidationError("Could not send the form.")
        return attrs

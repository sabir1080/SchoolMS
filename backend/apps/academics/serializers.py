from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from apps.accounts.models import Role, User
from apps.core.serializers import TenantPrimaryKeyRelatedField

from .models import AcademicSession, Program, Section, Subject


class TenantUniqueNameMixin:
    """Friendly "already exists" error for names that must be unique within an institute."""

    def validate_name(self, value):
        value = value.strip()
        tenant = self.context["request"].user.tenant
        others = self.Meta.model.objects.filter(tenant=tenant, name__iexact=value)
        if self.instance is not None:
            others = others.exclude(pk=self.instance.pk)
        if others.exists():
            raise serializers.ValidationError(f'"{value}" already exists.')
        return value


class AcademicSessionSerializer(TenantUniqueNameMixin, serializers.ModelSerializer):
    class Meta:
        model = AcademicSession
        fields = ["id", "name", "start_date", "end_date", "is_current"]

    def validate(self, attrs):
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start and end and end <= start:
            raise serializers.ValidationError({"end_date": ["End date must be after the start date."]})
        return attrs


class SubjectSerializer(TenantUniqueNameMixin, serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ["id", "name", "code", "is_active"]


class ProgramSerializer(TenantUniqueNameMixin, serializers.ModelSerializer):
    subjects = TenantPrimaryKeyRelatedField(queryset=Subject.objects.all(), many=True, required=False)
    section_count = serializers.SerializerMethodField()

    class Meta:
        model = Program
        fields = ["id", "name", "code", "description", "sort_order", "is_active", "subjects", "section_count"]

    def get_section_count(self, program):
        return len(program.sections.all())


class SectionSerializer(serializers.ModelSerializer):
    program = TenantPrimaryKeyRelatedField(queryset=Program.objects.all())
    session = TenantPrimaryKeyRelatedField(queryset=AcademicSession.objects.all())
    class_teacher = TenantPrimaryKeyRelatedField(
        queryset=User.objects.filter(role__in=[Role.TEACHER, Role.ADMIN], is_active=True),
        required=False,
        allow_null=True,
    )
    program_name = serializers.CharField(source="program.name", read_only=True)
    session_name = serializers.CharField(source="session.name", read_only=True)
    class_teacher_name = serializers.SerializerMethodField()

    class Meta:
        model = Section
        fields = [
            "id", "program", "program_name", "session", "session_name", "name", "capacity",
            "class_teacher", "class_teacher_name", "is_active",
        ]
        validators = [
            UniqueTogetherValidator(
                queryset=Section.objects.all(),
                fields=["program", "session", "name"],
                message="This name is already used for this program in this session.",
            )
        ]

    def get_class_teacher_name(self, section):
        teacher = section.class_teacher
        if teacher is None:
            return None
        return " ".join(filter(None, [teacher.first_name, teacher.last_name])) or teacher.username

    def validate_name(self, value):
        return value.strip()


class BulkNamesSerializer(serializers.Serializer):
    names = serializers.ListField(
        child=serializers.CharField(max_length=100, allow_blank=True), allow_empty=False, max_length=100
    )

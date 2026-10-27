from rest_framework import serializers

from apps.academics.models import Section, Subject
from apps.accounts.models import Role, User
from apps.core.serializers import TenantPrimaryKeyRelatedField

from .models import DAY_NAMES, Period, TimetableEntry


class PeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = Period
        fields = ["id", "name", "start_time", "end_time", "is_break"]

    def validate(self, attrs):
        start = attrs.get("start_time", getattr(self.instance, "start_time", None))
        end = attrs.get("end_time", getattr(self.instance, "end_time", None))
        if start and end and end <= start:
            raise serializers.ValidationError({"end_time": ["Must be after the start time."]})
        attrs["name"] = attrs.get("name", getattr(self.instance, "name", "")).strip()
        return attrs


class GenerateSerializer(serializers.Serializer):
    start = serializers.TimeField()
    periods = serializers.IntegerField(min_value=1, max_value=12)
    minutes = serializers.IntegerField(min_value=10, max_value=120)
    break_after = serializers.IntegerField(min_value=0, max_value=12, default=0)
    break_minutes = serializers.IntegerField(min_value=5, max_value=90, default=20)


class EntrySerializer(serializers.ModelSerializer):
    section = TenantPrimaryKeyRelatedField(queryset=Section.objects.all())
    period = TenantPrimaryKeyRelatedField(queryset=Period.objects.all())
    subject = TenantPrimaryKeyRelatedField(queryset=Subject.objects.all(), allow_null=True, required=False)
    teacher = TenantPrimaryKeyRelatedField(queryset=User.objects.all(), allow_null=True, required=False)
    subject_name = serializers.CharField(source="subject.name", read_only=True, default=None)
    teacher_name = serializers.SerializerMethodField()
    section_name = serializers.SerializerMethodField()

    class Meta:
        model = TimetableEntry
        fields = ["id", "section", "section_name", "day", "period", "subject", "subject_name", "teacher", "teacher_name", "room"]
        validators = []  # the slot clash is checked in validate() with a clearer message

    def get_teacher_name(self, entry):
        return entry.teacher and (entry.teacher.get_full_name() or entry.teacher.username)

    def get_section_name(self, entry):
        return f"{entry.section.program.name} - {entry.section.name}"

    def validate(self, attrs):
        get = lambda field: attrs.get(field, getattr(self.instance, field, None))  # noqa: E731
        section, day, period, teacher = get("section"), get("day"), get("period"), get("teacher")
        if day is None or not 0 <= day <= 6:
            raise serializers.ValidationError({"day": ["Choose a weekday."]})
        if period.is_break:
            raise serializers.ValidationError({"period": ["Nothing can be scheduled in a break."]})
        if not get("subject"):
            raise serializers.ValidationError({"subject": ["Choose a subject."]})
        if teacher is not None and teacher.role not in (Role.TEACHER, Role.ADMIN):
            raise serializers.ValidationError({"teacher": ["Choose a teacher."]})
        same_slot = TimetableEntry.objects.filter(section=section, day=day, period=period)
        if self.instance is not None:
            same_slot = same_slot.exclude(pk=self.instance.pk)
        if same_slot.exists():
            raise serializers.ValidationError("This period already has a subject. Edit it instead.")
        if teacher is not None:
            clash = (
                TimetableEntry.objects.filter(teacher=teacher, day=day, period=period, section__session_id=section.session_id)
                .exclude(section=section)
                .select_related("section__program")
                .first()
            )
            if clash:
                name = teacher.get_full_name() or teacher.username
                raise serializers.ValidationError(
                    {"teacher": [f"{name} already teaches {clash.section.program.name} - {clash.section.name} "
                                 f"on {DAY_NAMES[day]} in {period.name}."]}
                )
        return attrs

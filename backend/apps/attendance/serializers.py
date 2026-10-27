from rest_framework import serializers

from apps.academics.models import Section
from apps.core.serializers import TenantPrimaryKeyRelatedField
from apps.core.timeutils import tenant_today

from .models import AttendanceStatus


class RecordInputSerializer(serializers.Serializer):
    student = serializers.IntegerField()
    status = serializers.ChoiceField(choices=AttendanceStatus.choices)
    remark = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")


class SheetInputSerializer(serializers.Serializer):
    section = TenantPrimaryKeyRelatedField(queryset=Section.objects.select_related("session"))
    date = serializers.DateField()
    records = RecordInputSerializer(many=True, allow_empty=False)

    def validate(self, attrs):
        section, date = attrs["section"], attrs["date"]
        if date > tenant_today(section.tenant):
            raise serializers.ValidationError({"date": ["Attendance cannot be marked for a future date."]})
        session = section.session
        if not (session.start_date <= date <= session.end_date):
            raise serializers.ValidationError(
                {"date": [f"The date must be within the session {session.name} ({session.start_date} to {session.end_date})."]}
            )
        ids = [r["student"] for r in attrs["records"]]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError({"records": ["Each student can appear only once."]})
        return attrs

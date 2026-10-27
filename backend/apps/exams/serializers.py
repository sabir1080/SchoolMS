from decimal import Decimal

from rest_framework import serializers

from apps.academics.models import AcademicSession, Program, Subject
from apps.core.serializers import TenantPrimaryKeyRelatedField

from .models import Exam, ExamSubject, GradeBand


class GradeBandSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradeBand
        fields = ["name", "min_percentage", "remark"]
        extra_kwargs = {"min_percentage": {"min_value": Decimal(0), "max_value": Decimal(100)}}


class GradingInputSerializer(serializers.Serializer):
    bands = GradeBandSerializer(many=True, allow_empty=False)

    def validate_bands(self, bands):
        names = [b["name"].strip().upper() for b in bands]
        if len(names) != len(set(names)) or not all(names):
            raise serializers.ValidationError("Every grade needs a different name.")
        mins = [b["min_percentage"] for b in bands]
        if len(mins) != len(set(mins)):
            raise serializers.ValidationError("Two grades cannot start at the same percentage.")
        if min(mins) != 0:
            raise serializers.ValidationError("The lowest grade must start at 0%.")
        return sorted(bands, key=lambda b: b["min_percentage"], reverse=True)


class ExamSerializer(serializers.ModelSerializer):
    session = TenantPrimaryKeyRelatedField(queryset=AcademicSession.objects.all())
    programs = TenantPrimaryKeyRelatedField(queryset=Program.objects.all(), many=True, allow_empty=False)
    session_name = serializers.CharField(source="session.name", read_only=True)
    program_names = serializers.SerializerMethodField()
    paper_count = serializers.SerializerMethodField()

    class Meta:
        model = Exam
        fields = [
            "id", "session", "session_name", "name", "exam_type", "start_date", "end_date", "status",
            "programs", "program_names", "notes", "paper_count",
        ]

    def get_program_names(self, exam):
        return [p.name for p in sorted(exam.programs.all(), key=lambda p: (p.sort_order, p.name))]

    def get_paper_count(self, exam):
        return len(exam.papers.all())

    def validate(self, attrs):
        session = attrs.get("session", getattr(self.instance, "session", None))
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        name = attrs.get("name", getattr(self.instance, "name", "")).strip()
        attrs["name"] = name
        if start and end and end < start:
            raise serializers.ValidationError({"end_date": ["End date cannot be before the start date."]})
        for field, value in (("start_date", start), ("end_date", end)):
            if value and not (session.start_date <= value <= session.end_date):
                raise serializers.ValidationError({field: [f"Must be within the session {session.name}."]})
        taken = Exam.objects.filter(session=session, name__iexact=name)
        if self.instance is not None:
            taken = taken.exclude(pk=self.instance.pk)
        if taken.exists():
            raise serializers.ValidationError({"name": [f'"{name}" already exists in {session.name}.']})
        return attrs


class PaperSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    program_name = serializers.CharField(source="program.name", read_only=True)

    class Meta:
        model = ExamSubject
        fields = ["id", "program", "program_name", "subject", "subject_name", "total_marks", "pass_marks", "date", "start_time"]


class PaperUpdateSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    total_marks = serializers.DecimalField(max_digits=6, decimal_places=2, min_value=Decimal(1))
    pass_marks = serializers.DecimalField(max_digits=6, decimal_places=2, min_value=Decimal(0))
    date = serializers.DateField(required=False, allow_null=True)
    start_time = serializers.TimeField(required=False, allow_null=True)

    def validate(self, attrs):
        if attrs["pass_marks"] > attrs["total_marks"]:
            raise serializers.ValidationError({"pass_marks": ["Pass marks cannot be more than total marks."]})
        return attrs


class PapersInputSerializer(serializers.Serializer):
    program = TenantPrimaryKeyRelatedField(queryset=Program.objects.all())
    papers = PaperUpdateSerializer(many=True, required=False, default=list)
    remove = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    add = TenantPrimaryKeyRelatedField(queryset=Subject.objects.all(), many=True, required=False, default=list)

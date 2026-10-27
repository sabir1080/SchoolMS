from decimal import Decimal

from rest_framework import serializers

from apps.academics.models import AcademicSession, Program, Subject
from apps.core.serializers import TenantPrimaryKeyRelatedField

from .models import CombinedExam, CombinedResult, Exam, ExamSubject, GradeBand


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


class MarkEntrySerializer(serializers.Serializer):
    student = serializers.IntegerField()
    marks = serializers.DecimalField(max_digits=6, decimal_places=2, min_value=Decimal(0), allow_null=True, required=False)
    absent = serializers.BooleanField(default=False)


class MarksInputSerializer(serializers.Serializer):
    section = serializers.IntegerField()
    paper = serializers.IntegerField()
    entries = MarkEntrySerializer(many=True)

    def validate_entries(self, entries):
        students = [e["student"] for e in entries]
        if len(students) != len(set(students)):
            raise serializers.ValidationError("A student appears twice.")
        return entries


class CombinedExamSerializer(serializers.Serializer):
    exam = TenantPrimaryKeyRelatedField(queryset=Exam.objects.all())
    weight = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=Decimal("0.01"), max_value=Decimal(100))


class CombinedResultSerializer(serializers.ModelSerializer):
    session = TenantPrimaryKeyRelatedField(queryset=AcademicSession.objects.all())
    session_name = serializers.CharField(source="session.name", read_only=True)
    components = CombinedExamSerializer(many=True, allow_empty=False)

    class Meta:
        model = CombinedResult
        fields = ["id", "session", "session_name", "name", "status", "components"]

    def to_representation(self, combined):
        data = super().to_representation(combined)
        data["components"] = [
            {"exam": c.exam_id, "exam_name": c.exam.name, "exam_status": c.exam.status, "weight": f"{c.weight.normalize():f}"}
            for c in combined.components.all()
        ]
        return data

    def validate(self, attrs):
        session = attrs.get("session", getattr(self.instance, "session", None))
        name = attrs.get("name", getattr(self.instance, "name", "")).strip()
        attrs["name"] = name
        components = attrs.get("components")
        if components is not None:
            exams = [c["exam"].pk for c in components]
            if len(exams) != len(set(exams)):
                raise serializers.ValidationError({"components": ["Each exam can be added only once."]})
            if any(c["exam"].session_id != session.pk for c in components):
                raise serializers.ValidationError({"components": [f"All exams must be from the session {session.name}."]})
            if sum(c["weight"] for c in components) != 100:
                raise serializers.ValidationError({"components": ["The weights must add up to 100%."]})
        taken = CombinedResult.objects.filter(session=session, name__iexact=name)
        if self.instance is not None:
            taken = taken.exclude(pk=self.instance.pk)
        if taken.exists():
            raise serializers.ValidationError({"name": [f'"{name}" already exists in {session.name}.']})
        return attrs

    def save_components(self, combined, components):
        if components is None:
            return
        combined.components.all().delete()
        CombinedExam.objects.bulk_create([CombinedExam(combined=combined, exam=c["exam"], weight=c["weight"]) for c in components])

    def create(self, validated_data):
        components = validated_data.pop("components")
        combined = CombinedResult.objects.create(**validated_data)
        self.save_components(combined, components)
        return combined

    def update(self, instance, validated_data):
        components = validated_data.pop("components", None)
        instance = super().update(instance, validated_data)
        self.save_components(instance, components)
        return instance

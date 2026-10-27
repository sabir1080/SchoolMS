from rest_framework import serializers

from apps.academics.models import Section, Subject
from apps.core.serializers import TenantPrimaryKeyRelatedField

from .models import Homework


class HomeworkSerializer(serializers.ModelSerializer):
    section = TenantPrimaryKeyRelatedField(queryset=Section.objects.all())
    subject = TenantPrimaryKeyRelatedField(queryset=Subject.objects.all(), allow_null=True, required=False)
    subject_name = serializers.CharField(source="subject.name", read_only=True, default=None)
    section_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()

    class Meta:
        model = Homework
        fields = [
            "id", "section", "section_name", "subject", "subject_name", "date", "due_date", "title", "details",
            "created_by_name", "can_edit",
        ]

    def get_section_name(self, hw):
        return f"{hw.section.program.name} - {hw.section.name}"

    def get_created_by_name(self, hw):
        return hw.created_by and (hw.created_by.get_full_name() or hw.created_by.username)

    def get_can_edit(self, hw):
        user = self.context.get("request") and self.context["request"].user
        return bool(user and (user.role == "admin" or hw.created_by_id == user.pk))

    def validate(self, attrs):
        date = attrs.get("date", getattr(self.instance, "date", None))
        due = attrs.get("due_date", getattr(self.instance, "due_date", None))
        if date and due and due < date:
            raise serializers.ValidationError({"due_date": ["The due date cannot be before the diary date."]})
        attrs["title"] = attrs.get("title", getattr(self.instance, "title", "")).strip()
        if not attrs["title"]:
            raise serializers.ValidationError({"title": ["Write what the homework is."]})
        return attrs

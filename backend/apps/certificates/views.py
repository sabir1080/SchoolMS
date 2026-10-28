from django.db import transaction
from django.db.models import Max
from rest_framework import mixins, serializers, viewsets
from rest_framework.exceptions import ValidationError

from apps.core.mixins import TenantScopedViewSetMixin
from apps.core.permissions import IsInstituteAdmin
from apps.core.serializers import TenantPrimaryKeyRelatedField
from apps.core.timeutils import tenant_today
from apps.recyclebin.mixins import RecycleBinMixin
from apps.students.models import Student, StudentGuardian, StudentStatus
from apps.students.serializers import current_enrollment
from apps.students.services import lock_tenant, sync_login_status
from apps.subscriptions.features import Feature

from .models import Certificate, Kind


class CertificateSerializer(serializers.ModelSerializer):
    student = TenantPrimaryKeyRelatedField(queryset=Student.objects.all())
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    issued_on = serializers.DateField(required=False)
    # Details typed by the admin (kept in ``data``)
    conduct = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=60)
    purpose = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=150)
    leaving_date = serializers.DateField(write_only=True, required=False, allow_null=True)
    reason = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=150)
    remarks = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=300)
    mark_left = serializers.BooleanField(write_only=True, required=False, default=False)

    class Meta:
        model = Certificate
        fields = ["id", "student", "kind", "kind_label", "number", "issued_on", "data", "conduct", "purpose",
                  "leaving_date", "reason", "remarks", "mark_left"]
        read_only_fields = ["number", "data"]

    def validate(self, attrs):
        if attrs["kind"] == Kind.LEAVING:
            if not attrs.get("leaving_date"):
                raise ValidationError({"leaving_date": ["Enter the date the student left."]})
            if not attrs.get("reason", "").strip():
                raise ValidationError({"reason": ["Enter the reason for leaving."]})
        return attrs


def snapshot(student, extra):
    """The student's details for the certificate text, as they are today."""
    student = Student.objects.prefetch_related("enrollments__session", "enrollments__section__program").get(pk=student.pk)
    enrollment = current_enrollment(student)
    link = StudentGuardian.objects.filter(student=student).select_related("guardian").order_by("-is_primary", "id").first()
    return {
        "full_name": student.full_name,
        "gender": student.gender,
        "father_name": link.guardian.name if link else "",
        "relation": link.relation if link else "",
        "admission_no": student.admission_no,
        "admission_date": student.admission_date.isoformat() if student.admission_date else None,
        "date_of_birth": student.date_of_birth.isoformat() if student.date_of_birth else None,
        "class_name": f"{enrollment.section.program.name} - {enrollment.section.name}" if enrollment else "",
        "program_name": enrollment.section.program.name if enrollment else "",
        "roll_number": enrollment.roll_number if enrollment else "",
        "session_name": enrollment.session.name if enrollment else "",
        **extra,
    }


class CertificateViewSet(RecycleBinMixin, TenantScopedViewSetMixin, mixins.CreateModelMixin, mixins.ListModelMixin,
                         mixins.RetrieveModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """Issue, list (?student=), reprint and cancel certificates. Admins only."""

    queryset = Certificate.objects.select_related("student")
    serializer_class = CertificateSerializer
    permission_classes = [IsInstituteAdmin]
    required_feature = Feature.CERTIFICATES

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.query_params.get("student"):
            queryset = queryset.filter(student_id=self.request.query_params["student"])
        return queryset

    def perform_create(self, serializer):
        data = serializer.validated_data
        extra = {key: data.pop(key) for key in ("conduct", "purpose", "reason", "remarks") if key in data}
        extra = {k: v.strip() for k, v in extra.items()}
        leaving_date = data.pop("leaving_date", None)
        mark_left = data.pop("mark_left", False)
        if leaving_date:
            extra["leaving_date"] = leaving_date.isoformat()
        extra.setdefault("conduct", "Good")
        tenant = self.get_tenant()
        with transaction.atomic():
            tenant = lock_tenant(tenant)
            number = (Certificate.objects.filter(tenant=tenant).aggregate(m=Max("number"))["m"] or 0) + 1
            student = data["student"]
            serializer.save(
                tenant=tenant, number=number, issued_on=data.get("issued_on") or tenant_today(tenant),
                data=snapshot(student, extra), issued_by=self.request.user,
            )
            if data["kind"] == Kind.LEAVING and mark_left and student.status == StudentStatus.ACTIVE:
                student.status = StudentStatus.LEFT
                student.save(update_fields=["status", "updated_at"])
                sync_login_status(student)

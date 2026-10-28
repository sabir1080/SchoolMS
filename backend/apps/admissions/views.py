from django.db import transaction
from django.utils import timezone
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.academics.models import Program, Section
from apps.core.mixins import TenantScopedViewSetMixin
from apps.core.permissions import IsInstituteAdmin
from apps.core.serializers import TenantPrimaryKeyRelatedField
from apps.fees.services import next_number
from apps.messaging.models import Kind
from apps.messaging.services import queue_and_send
from apps.recyclebin.mixins import RecycleBinMixin
from apps.students.serializers import StudentWriteSerializer
from apps.students.services import lock_tenant
from apps.subscriptions.features import Feature
from apps.tenants.models import Tenant
from apps.tenants.serializers import BrandingFieldsMixin
from apps.tenants.validators import normalize_code

from .models import Application, Status
from .rules import admissions_open
from .serializers import ApplicationSerializer, PublicApplicationSerializer


class PublicFormSerializer(BrandingFieldsMixin, serializers.ModelSerializer):
    open = serializers.SerializerMethodField()
    programs = serializers.SerializerMethodField()

    class Meta:
        model = Tenant
        fields = ["name", "slug", "institute_type", "address", "phone", "brand", "open", "programs"]

    def get_open(self, tenant):
        return admissions_open(tenant)

    def get_programs(self, tenant):
        if not admissions_open(tenant):
            return []
        return list(Program.objects.filter(tenant=tenant, is_active=True).values("id", "name"))


class PublicAdmissionView(APIView):
    """The institute's online admission form (no login): GET shows it, POST sends an application."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def get_throttles(self):
        self.throttle_scope = "admission" if self.request.method == "POST" else "lookup"
        return super().get_throttles()

    def tenant(self):
        tenant = Tenant.objects.filter(slug=normalize_code(self.kwargs["code"])).first()
        if tenant is None or not tenant.is_active:
            raise NotFound("Institute code not found.")
        return tenant

    def get(self, request, code):
        return Response(PublicFormSerializer(self.tenant()).data)

    def post(self, request, code):
        tenant = self.tenant()
        if not admissions_open(tenant):
            raise ValidationError("This institute is not taking online admissions right now.")
        serializer = PublicApplicationSerializer(data=request.data, context={"tenant": tenant})
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            tenant = lock_tenant(tenant)
            app = serializer.save(tenant=tenant, number=next_number(Application, "number", tenant))
        return Response({"number": app.number, "full_name": app.full_name}, status=status.HTTP_201_CREATED)


class ApproveSerializer(serializers.Serializer):
    section = TenantPrimaryKeyRelatedField(queryset=Section.objects.all(), required=False, allow_null=True)
    roll_number = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")
    admission_no = serializers.CharField(max_length=30, required=False, allow_blank=True, default="")


class ApplicationViewSet(RecycleBinMixin, TenantScopedViewSetMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                         mixins.UpdateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """Admins review applications: admit (creates the student) or decline."""

    queryset = Application.objects.select_related("program", "decided_by")
    serializer_class = ApplicationSerializer
    permission_classes = [IsInstituteAdmin]
    required_feature = Feature.ADMISSIONS
    pagination_class = None

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.query_params.get("status"):
            queryset = queryset.filter(status=self.request.query_params["status"])
        return queryset

    def undecided(self):
        app = self.get_object()
        if app.status != Status.NEW:
            raise ValidationError("This application has already been decided.")
        return app

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        app = self.undecided()
        choice = ApproveSerializer(data=request.data, context={"request": request})
        choice.is_valid(raise_exception=True)
        section = choice.validated_data.get("section")
        data = {
            "first_name": app.first_name, "last_name": app.last_name, "gender": app.gender,
            "date_of_birth": app.date_of_birth, "address": app.address, "previous_school": app.previous_school,
            "admission_no": choice.validated_data["admission_no"],
            "notes": f"Online application No. {app.number}",
            "guardians": [{
                "name": app.guardian_name, "phone": app.guardian_phone, "email": app.guardian_email,
                "cnic": app.guardian_cnic, "relation": app.guardian_relation, "is_primary": True,
            }],
        }
        if section:
            data["enrollment"] = {"section": section.pk, "roll_number": choice.validated_data["roll_number"]}
        student_serializer = StudentWriteSerializer(data=data, context={"request": request})
        student_serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            student = student_serializer.save()
            app.status, app.student, app.decided_at, app.decided_by = Status.APPROVED, student, timezone.now(), request.user
            app.save()
        where = f" in {section.program.name} - {section.name}" if section else ""
        queue_and_send(app.tenant, [(
            student,
            f"{app.tenant.name}: Congratulations! {student.full_name} has been given admission{where}. "
            f"Admission No. {student.admission_no}. Please contact the school office for the next steps.",
            f"admit:{app.pk}",
        )], Kind.NOTICE, request.user)
        return Response(self.get_serializer(app).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        app = self.undecided()
        app.status, app.decided_at, app.decided_by = Status.REJECTED, timezone.now(), request.user
        app.admin_note = str(request.data.get("admin_note", app.admin_note))[:255]
        app.save()
        return Response(self.get_serializer(app).data)

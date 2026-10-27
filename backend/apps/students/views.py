from django.db import IntegrityError, transaction
from django.db.models import Prefetch, Q
from django.db.models.deletion import ProtectedError
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response

from apps.accounts.models import Role
from apps.core.mixins import TenantScopedViewSetMixin
from apps.core.permissions import AdminWriteStaffRead, HasRole
from apps.subscriptions.features import Feature
from apps.subscriptions.gating import ActiveSubscription, RequiresFeature

from .models import Enrollment, Guardian, Student, StudentGuardian, StudentStatus
from .serializers import (
    CreateLoginSerializer,
    EnrollInputSerializer,
    GuardianSerializer,
    MyChildSerializer,
    StudentDetailSerializer,
    StudentListSerializer,
    StudentWriteSerializer,
    current_enrollment,
    primary_link,
)
from .services import current_session, enroll


def student_queryset():
    return Student.objects.prefetch_related(
        Prefetch("enrollments", queryset=Enrollment.objects.select_related("section__program", "session")),
        Prefetch("guardian_links", queryset=StudentGuardian.objects.select_related("guardian__user").prefetch_related("guardian__students")),
    ).select_related("user")


class StudentViewSet(TenantScopedViewSetMixin, viewsets.ModelViewSet):
    """Admissions: admins add and edit students; teachers can look them up."""

    permission_classes = [AdminWriteStaffRead]
    required_feature = Feature.STUDENTS

    queryset = student_queryset()

    def get_queryset(self):
        queryset = self.filter_queryset_by_params(super().get_queryset())
        # Photos are only needed on a student's own page and on ID cards.
        return queryset.defer("photo") if self.action == "list" else queryset

    def filter_queryset_by_params(self, queryset):
        params = self.request.query_params
        if params.get("search"):
            term = params["search"].strip()
            queryset = queryset.filter(
                Q(first_name__icontains=term)
                | Q(last_name__icontains=term)
                | Q(admission_no__icontains=term)
                | Q(guardian_links__guardian__phone__icontains=term)
                | Q(guardian_links__guardian__name__icontains=term)
            ).distinct()
        if params.get("status"):
            queryset = queryset.filter(status=params["status"])
        # Class filters apply to a session: the one asked for, else the current one.
        session_id = params.get("session") or getattr(current_session(self.get_tenant()), "pk", None)
        if params.get("section"):
            queryset = queryset.filter(enrollments__section_id=params["section"])
        elif params.get("program"):
            queryset = queryset.filter(enrollments__section__program_id=params["program"], enrollments__session_id=session_id)
        if params.get("unassigned") == "1":
            queryset = queryset.exclude(enrollments__session_id=session_id)
        return queryset

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return StudentWriteSerializer
        if self.action == "list":
            return StudentListSerializer
        return StudentDetailSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        student = serializer.save()
        return Response(self.detail_data(student), status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        serializer = self.get_serializer(self.get_object(), data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        student = serializer.save()
        return Response(self.detail_data(student))

    def detail_data(self, student):
        student = student_queryset().get(pk=student.pk)
        return StudentDetailSerializer(student, context=self.get_serializer_context()).data

    def perform_destroy(self, instance):
        try:
            with transaction.atomic():
                user = instance.user
                instance.delete()
                if user is not None:
                    user.delete()
        except ProtectedError:
            raise ValidationError("This student has records and cannot be deleted. Mark them as Left instead.")

    @action(detail=False, methods=["get"], url_path="id-cards")
    def id_cards(self, request):
        """Card details for printing ID cards: one section (``?section=``) or chosen students (``?ids=1,2``)."""
        params = request.query_params
        queryset = super().get_queryset().filter(status=StudentStatus.ACTIVE)
        if params.get("section"):
            queryset = queryset.filter(enrollments__section_id=params["section"])
        elif params.get("ids"):
            ids = [int(i) for i in params["ids"].split(",") if i.strip().isdigit()][:200]
            queryset = queryset.filter(pk__in=ids)
        else:
            raise ValidationError("Choose a section or students.")
        tenant = self.get_tenant()
        cards = []
        for student in queryset.distinct():
            enrollment = current_enrollment(student)
            link = primary_link(student)
            cards.append({
                "id": student.id, "full_name": student.full_name, "admission_no": student.admission_no,
                "photo": student.photo, "date_of_birth": student.date_of_birth, "blood_group": student.blood_group,
                "class_name": f"{enrollment.section.program.name} - {enrollment.section.name}" if enrollment else None,
                "roll_number": enrollment.roll_number if enrollment else "",
                "valid_until": enrollment.session.end_date if enrollment else None,
                "guardian_name": link.guardian.name if link else "",
                "guardian_relation": link.get_relation_display() if link else "",
                "guardian_phone": link.guardian.phone if link else "",
            })
        cards.sort(key=lambda c: (c["roll_number"].zfill(6) if c["roll_number"].isdigit() else c["roll_number"] or "~", c["full_name"]))
        return Response({
            "institute": {"name": tenant.name, "address": tenant.address, "phone": tenant.phone, "code": tenant.slug},
            "cards": cards,
        })

    @action(detail=True, methods=["post"])
    def enroll(self, request, pk=None):
        """Put the student in a section (class/batch); replaces their section for that session."""
        student = self.get_object()
        serializer = EnrollInputSerializer(data=request.data, context={**self.get_serializer_context(), "student": student})
        serializer.is_valid(raise_exception=True)
        try:
            enroll(student, serializer.validated_data["section"], serializer.validated_data["roll_number"])
        except IntegrityError:
            raise ValidationError({"roll_number": ["Roll number already used in this section."]})
        return Response(self.detail_data(student))

    @action(detail=True, methods=["delete"], url_path="enrollments/(?P<enrollment_id>[^/.]+)")
    def remove_enrollment(self, request, pk=None, enrollment_id=None):
        student = self.get_object()
        deleted, _ = Enrollment.objects.filter(student=student, pk=enrollment_id).delete()
        if not deleted:
            raise NotFound()
        return Response(self.detail_data(student))

    @action(detail=True, methods=["post"], url_path="create-login")
    def create_login(self, request, pk=None):
        student = self.get_object()
        if student.user_id:
            raise ValidationError("This student already has a login.")
        serializer = CreateLoginSerializer(data=request.data, context={"tenant": self.get_tenant()})
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            student.user = serializer.create_user(Role.STUDENT, student.first_name, student.last_name, student.email)
            student.user.is_active = student.status == StudentStatus.ACTIVE
            student.user.save(update_fields=["is_active"])
            student.save(update_fields=["user"])
        return Response(self.detail_data(student), status=status.HTTP_201_CREATED)


class GuardianViewSet(TenantScopedViewSetMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                      mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """Look up guardians (e.g. by phone when admitting a sibling), edit them, give them a login."""

    queryset = Guardian.objects.select_related("user").prefetch_related("students")
    serializer_class = GuardianSerializer
    permission_classes = [AdminWriteStaffRead]
    required_feature = Feature.STUDENTS

    def get_queryset(self):
        queryset = super().get_queryset()
        phone = self.request.query_params.get("phone", "").strip()
        if phone:
            queryset = queryset.filter(phone=phone)
        return queryset

    @action(detail=True, methods=["post"], url_path="create-login")
    def create_login(self, request, pk=None):
        guardian = self.get_object()
        if guardian.user_id:
            raise ValidationError("This guardian already has a login.")
        serializer = CreateLoginSerializer(data=request.data, context={"tenant": self.get_tenant()})
        serializer.is_valid(raise_exception=True)
        first, _, last = guardian.name.partition(" ")
        with transaction.atomic():
            guardian.user = serializer.create_user(Role.PARENT, first, last, guardian.email)
            guardian.save(update_fields=["user"])
        return Response(self.get_serializer(guardian).data, status=status.HTTP_201_CREATED)


class PortalView:
    """Shared settings for the parent and student portal endpoints."""

    pagination_class = None

    def get_permissions(self):
        return [*super().get_permissions(), ActiveSubscription(), RequiresFeature()]

    required_feature = Feature.STUDENTS


class MyChildrenView(PortalView, ListAPIView):
    """A parent's children."""

    serializer_class = MyChildSerializer
    permission_classes = [HasRole.for_roles(Role.PARENT)]

    def get_queryset(self):
        guardian = getattr(self.request.user, "guardian_profile", None)
        if guardian is None:
            return Student.objects.none()
        return student_queryset().filter(guardian_links__guardian=guardian)


class MyStudentProfileView(PortalView, RetrieveAPIView):
    """A student's own profile."""

    serializer_class = MyChildSerializer
    permission_classes = [HasRole.for_roles(Role.STUDENT)]

    def get_object(self):
        student = getattr(self.request.user, "student_profile", None)
        if student is None:
            raise NotFound("No student profile is linked to this login.")
        return student_queryset().get(pk=student.pk)


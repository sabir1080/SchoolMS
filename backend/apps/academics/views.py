from django.db import IntegrityError, transaction
from django.db.models import Max, ProtectedError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.core.mixins import TenantScopedViewSetMixin
from apps.core.permissions import AdminWriteStaffRead
from apps.recyclebin.services import trash
from apps.subscriptions.features import Feature

from .models import AcademicSession, Program, Section, Subject
from .serializers import (
    AcademicSessionSerializer,
    BulkNamesSerializer,
    ProgramSerializer,
    ReorderSerializer,
    SectionSerializer,
    SubjectSerializer,
)


class AcademicsViewSet(TenantScopedViewSetMixin, viewsets.ModelViewSet):
    """Base for academic setup: admins edit, teachers read, plan must include academics."""

    permission_classes = [AdminWriteStaffRead]
    required_feature = Feature.ACADEMICS

    def perform_destroy(self, instance):
        try:
            trash(instance, self.request.user)
        except ProtectedError:
            raise ValidationError(
                f'"{instance}" is in use and cannot be deleted. Mark it inactive instead.', code="in_use"
            )


class BulkCreateByNameMixin:
    """``POST .../bulk-create/ {"names": [...]}`` adds many rows at once, skipping existing names."""

    @action(detail=False, methods=["post"], url_path="bulk-create")
    def bulk_create(self, request):
        data = BulkNamesSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        tenant = self.get_tenant()
        model = self.queryset.model
        existing = {name.lower() for name in model.objects.filter(tenant=tenant).values_list("name", flat=True)}
        created = []
        # New programs go after the existing ones, in the order they were typed.
        next_order = (model.objects.filter(tenant=tenant).aggregate(m=Max("sort_order"))["m"] or 0) + 1 if model is Program else 0
        with transaction.atomic():
            for raw in data.validated_data["names"]:
                name = raw.strip()
                if not name or name.lower() in existing:
                    continue
                extra = {}
                if model is Program:
                    extra = {"sort_order": next_order}
                    next_order += 1
                created.append(model.objects.create(tenant=tenant, name=name, **extra))
                existing.add(name.lower())
        serializer = self.get_serializer(created, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AcademicSessionViewSet(AcademicsViewSet):
    queryset = AcademicSession.objects.all()
    serializer_class = AcademicSessionSerializer

    def perform_create(self, serializer):
        # The first session an institute creates becomes the current one.
        first = not AcademicSession.objects.filter(tenant=self.get_tenant()).exists()
        if first:
            serializer.save(tenant=self.get_tenant(), is_current=True)
        else:
            super().perform_create(serializer)


class SubjectViewSet(BulkCreateByNameMixin, AcademicsViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer


class ProgramViewSet(BulkCreateByNameMixin, AcademicsViewSet):
    queryset = Program.objects.prefetch_related("subjects", "sections")
    serializer_class = ProgramSerializer

    @action(detail=False, methods=["post"])
    def reorder(self, request):
        """``POST .../reorder/ {"ids": [...]}`` with every program id in the new display order."""
        data = ReorderSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        ids = data.validated_data["ids"]
        programs = {p.pk: p for p in Program.objects.filter(tenant=self.get_tenant())}
        if len(ids) != len(set(ids)) or set(ids) != set(programs):
            raise ValidationError({"ids": ["Send every program exactly once."]})
        for order, pk in enumerate(ids, start=1):
            programs[pk].sort_order = order
        Program.objects.bulk_update(programs.values(), ["sort_order"])
        return Response(self.get_serializer(self.get_queryset(), many=True).data)


class SectionViewSet(AcademicsViewSet):
    queryset = Section.objects.select_related("program", "session", "class_teacher")
    serializer_class = SectionSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params
        if params.get("session"):
            queryset = queryset.filter(session_id=params["session"])
        if params.get("program"):
            queryset = queryset.filter(program_id=params["program"])
        return queryset

    def perform_create(self, serializer):
        try:
            super().perform_create(serializer)
        except IntegrityError:
            raise ValidationError({"name": ["This name is already used for this program in this session."]})

import datetime

from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.academics.models import Section
from apps.accounts.models import Role
from apps.attendance.views import section_label
from apps.core.mixins import TenantScopedViewSetMixin
from apps.core.permissions import HasRole
from apps.core.timeutils import tenant_today
from apps.exams.views import my_student
from apps.students.serializers import current_enrollment
from apps.subscriptions.features import Feature
from apps.subscriptions.gating import ActiveSubscription, RequiresFeature

from .models import Homework
from .serializers import HomeworkSerializer


def postable_sections(user):
    """Current-session sections a user may write the diary for: all for admins; for teachers their own
    sections (class teacher) and the sections they teach in the timetable."""
    sections = Section.objects.filter(tenant=user.tenant, session__is_current=True, is_active=True).select_related("program", "session")
    if user.role == Role.TEACHER:
        sections = sections.filter(Q(class_teacher=user) | Q(timetable__teacher=user)).distinct()
    return sorted(sections, key=lambda s: (s.program.sort_order, s.program.name, s.name))


class HomeworkViewSet(TenantScopedViewSetMixin, viewsets.ModelViewSet):
    """The class diary. ?section= and ?date= (default today). Teachers write for their sections and edit their own entries."""

    queryset = Homework.objects.select_related("section__program", "subject", "created_by")
    serializer_class = HomeworkSerializer
    permission_classes = [HasRole.for_roles(Role.ADMIN, Role.TEACHER)]
    required_feature = Feature.HOMEWORK
    pagination_class = None

    def allowed_ids(self):
        return {s.id for s in postable_sections(self.request.user)}

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role == Role.TEACHER:
            queryset = queryset.filter(section_id__in=self.allowed_ids())
        if self.action != "list":
            return queryset
        params = self.request.query_params
        if params.get("section"):
            queryset = queryset.filter(section_id=params["section"])
        try:
            date = datetime.date.fromisoformat(params["date"]) if params.get("date") else tenant_today(self.get_tenant())
        except ValueError:
            raise ValidationError({"date": ["Use the format YYYY-MM-DD."]})
        return queryset.filter(date=date)

    def check_section(self, section):
        if section.id not in self.allowed_ids():
            raise PermissionDenied("You can only write the diary for your own sections.")

    def check_owner(self, homework):
        if self.request.user.role != Role.ADMIN and homework.created_by_id != self.request.user.pk:
            raise PermissionDenied("Only the teacher who wrote it (or an admin) can change it.")

    def perform_create(self, serializer):
        self.check_section(serializer.validated_data["section"])
        homework = serializer.save(tenant=self.get_tenant(), created_by=self.request.user)
        from apps.messaging.alerts import homework_alerts

        homework_alerts(homework, self.request.user)

    def perform_update(self, serializer):
        self.check_owner(serializer.instance)
        if "section" in serializer.validated_data:
            self.check_section(serializer.validated_data["section"])
        serializer.save()

    def perform_destroy(self, instance):
        self.check_owner(instance)
        instance.delete()

    @action(detail=False)
    def sections(self, request):
        return Response([{**section_label(s), "program": s.program_id} for s in postable_sections(request.user)])


class MyHomeworkView(APIView):
    """Parents (?student=) and students: the diary of the child's section for the last two weeks and anything still due."""

    required_feature = Feature.HOMEWORK

    def get_permissions(self):
        return [HasRole.for_roles(Role.PARENT, Role.STUDENT)(), ActiveSubscription(), RequiresFeature()]

    def get(self, request):
        student = my_student(request)
        enrollment = current_enrollment(student)
        if enrollment is None or not enrollment.session.is_current:
            raise NotFound("Not in a class this session.")
        today = tenant_today(request.user.tenant)
        entries = Homework.objects.filter(section_id=enrollment.section_id).filter(
            Q(date__gte=today - datetime.timedelta(days=14)) | Q(due_date__gte=today)
        ).select_related("section__program", "subject", "created_by")
        return Response({"today": today, "entries": HomeworkSerializer(entries[:60], many=True, context={"request": request}).data})

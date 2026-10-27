import datetime

from django.db import transaction
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.academics.models import Section
from apps.accounts.models import Role
from apps.attendance.views import section_label
from apps.core.mixins import TenantScopedViewSetMixin
from apps.core.permissions import AdminWriteStaffRead, HasRole
from apps.core.timeutils import tenant_today
from apps.exams.views import my_student
from apps.students.serializers import current_enrollment
from apps.subscriptions.features import Feature
from apps.subscriptions.gating import ActiveSubscription, RequiresFeature

from .models import DAY_NAMES, Period, TimetableEntry
from .serializers import EntrySerializer, GenerateSerializer, PeriodSerializer


def working_days(tenant):
    return [int(d) for d in tenant.working_days.split(",") if d.strip().isdigit()]


def timetable_payload(tenant, entries):
    return {
        "days": [{"day": d, "name": DAY_NAMES[d]} for d in working_days(tenant)],
        "periods": PeriodSerializer(Period.objects.filter(tenant=tenant), many=True).data,
        "entries": EntrySerializer(entries, many=True).data,
        "today": tenant_today(tenant).weekday(),
    }


class PeriodViewSet(TenantScopedViewSetMixin, viewsets.ModelViewSet):
    """The bell schedule. Admins edit; teachers read."""

    queryset = Period.objects.all()
    serializer_class = PeriodSerializer
    permission_classes = [AdminWriteStaffRead]
    required_feature = Feature.TIMETABLE
    pagination_class = None

    @action(detail=False, methods=["post"])
    def generate(self, request):
        """Make the whole day at once: N periods of M minutes from a start time, with one break."""
        tenant = self.get_tenant()
        if TimetableEntry.objects.filter(tenant=tenant).exists():
            raise ValidationError("The timetable already uses these periods. Edit them one by one instead.")
        serializer = GenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        now = datetime.datetime.combine(datetime.date(2000, 1, 1), data["start"])
        rows = []
        for number in range(1, data["periods"] + 1):
            end = now + datetime.timedelta(minutes=data["minutes"])
            rows.append(Period(tenant=tenant, name=f"Period {number}", start_time=now.time(), end_time=end.time()))
            now = end
            if number == data["break_after"] and number < data["periods"]:
                end = now + datetime.timedelta(minutes=data["break_minutes"])
                rows.append(Period(tenant=tenant, name="Break", start_time=now.time(), end_time=end.time(), is_break=True))
                now = end
        if now.date() != datetime.date(2000, 1, 1):
            raise ValidationError("The school day would go past midnight.")
        with transaction.atomic():
            Period.objects.filter(tenant=tenant).delete()
            Period.objects.bulk_create(rows)
        return Response(PeriodSerializer(Period.objects.filter(tenant=tenant), many=True).data)


class EntryViewSet(TenantScopedViewSetMixin, viewsets.ModelViewSet):
    """Timetable entries. ?section= for a class, ?teacher= (or "me") for a teacher. Admins edit."""

    queryset = TimetableEntry.objects.select_related("section__program", "period", "subject", "teacher")
    serializer_class = EntrySerializer
    permission_classes = [AdminWriteStaffRead]
    required_feature = Feature.TIMETABLE
    pagination_class = None

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params
        if self.action != "list":
            return queryset
        if params.get("section"):
            return queryset.filter(section_id=params["section"])
        teacher = params.get("teacher")
        if teacher:
            teacher_id = self.request.user.pk if teacher == "me" else teacher
            return queryset.filter(teacher_id=teacher_id, section__session__is_current=True)
        raise ValidationError("Choose a section or a teacher.")

    def list(self, request, *args, **kwargs):
        return Response(timetable_payload(self.get_tenant(), self.filter_queryset(self.get_queryset())))


class MyTimetableView(APIView):
    """Parents (?student=) and students: the timetable of the child's section in the current session."""

    required_feature = Feature.TIMETABLE

    def get_permissions(self):
        return [HasRole.for_roles(Role.PARENT, Role.STUDENT)(), ActiveSubscription(), RequiresFeature()]

    def get(self, request):
        student = my_student(request)
        enrollment = current_enrollment(student)
        if enrollment is None or not enrollment.session.is_current:
            raise NotFound("Not in a class this session.")
        section = Section.objects.select_related("program", "session").get(pk=enrollment.section_id)
        entries = TimetableEntry.objects.filter(section=section).select_related("section__program", "period", "subject", "teacher")
        return Response({"section": section_label(section), **timetable_payload(request.user.tenant, entries)})

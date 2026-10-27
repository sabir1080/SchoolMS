import datetime

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.academics.models import Section
from apps.accounts.models import Role
from apps.core.permissions import HasRole
from apps.core.timeutils import parse_month, tenant_today
from apps.students.models import Enrollment, Student, StudentStatus
from apps.students.services import current_session
from apps.subscriptions.features import Feature
from apps.subscriptions.gating import ActiveSubscription, RequiresFeature

from .models import AttendanceRecord, summarize
from .serializers import SheetInputSerializer


def roll_sort_key(enrollment):
    roll = enrollment.roll_number
    return (0, int(roll), "") if roll.isdigit() else (1, 0, roll or "~"), enrollment.student.full_name.lower()


def section_label(section):
    return {"id": section.id, "program_name": section.program.name, "name": section.name, "session_name": section.session.name}


class AttendanceView(APIView):
    """Base: institute staff, usable subscription, plan includes attendance."""

    required_feature = Feature.ATTENDANCE
    allowed_roles = (Role.ADMIN, Role.TEACHER)

    def get_permissions(self):
        return [HasRole.for_roles(*self.allowed_roles)(), ActiveSubscription(), RequiresFeature()]

    @property
    def tenant(self):
        return self.request.user.tenant

    @property
    def today(self):
        return tenant_today(self.tenant)

    def accessible_sections(self):
        """Sections this user may mark: all for admins, their own (class teacher) for teachers."""
        sections = Section.objects.filter(tenant=self.tenant).select_related("program", "session", "class_teacher")
        if self.request.user.role == Role.TEACHER:
            sections = sections.filter(class_teacher=self.request.user)
        return sections

    def get_section(self, section_id):
        if not section_id:
            raise ValidationError({"section": ["This field is required."]})
        section = Section.objects.filter(tenant=self.tenant, pk=section_id).select_related("program", "session").first()
        if section is None:
            raise NotFound("Section not found.")
        if not self.accessible_sections().filter(pk=section.pk).exists():
            raise PermissionDenied("Only the class teacher or an admin can take attendance for this section.")
        return section

    def enrollments(self, section):
        """Active students in the section, in roll-number order."""
        rows = Enrollment.objects.filter(section=section, student__status=StudentStatus.ACTIVE).select_related("student")
        return sorted(rows, key=roll_sort_key)


class MySectionsView(AttendanceView):
    """Sections in the current session the user can take attendance for, with today's status."""

    def get(self, request):
        session = current_session(self.tenant)
        if session is None:
            return Response([])
        today = self.today
        sections = self.accessible_sections().filter(session=session, is_active=True)
        sections = sorted(sections, key=lambda s: (s.program.sort_order, s.program.name, s.name))
        marked = set(
            AttendanceRecord.objects.filter(tenant=self.tenant, date=today, section__in=sections)
            .values_list("section_id", flat=True)
            .distinct()
        )
        counts = {}
        for row in Enrollment.objects.filter(section__in=sections, student__status=StudentStatus.ACTIVE).values("section_id"):
            counts[row["section_id"]] = counts.get(row["section_id"], 0) + 1
        return Response(
            [
                {
                    **section_label(s),
                    "class_teacher_name": s.class_teacher and (s.class_teacher.get_full_name() or s.class_teacher.username),
                    "student_count": counts.get(s.id, 0),
                    "marked_today": s.id in marked,
                }
                for s in sections
            ]
        )


class SheetView(AttendanceView):
    """GET: the attendance sheet for a section and date. POST: save it."""

    def sheet(self, section, date):
        enrollments = self.enrollments(section)
        records = {
            r.student_id: r
            for r in AttendanceRecord.objects.filter(student__in=[e.student_id for e in enrollments], date=date)
        }
        students = [
            {
                "student": e.student_id,
                "admission_no": e.student.admission_no,
                "full_name": e.student.full_name,
                "roll_number": e.roll_number,
                "status": records[e.student_id].status if e.student_id in records else None,
                "remark": records[e.student_id].remark if e.student_id in records else "",
            }
            for e in enrollments
        ]
        return {
            "section": section_label(section),
            "date": date,
            "marked": bool(records),
            "students": students,
            "summary": summarize(r.status for r in records.values()),
        }

    def get(self, request):
        section = self.get_section(request.query_params.get("section"))
        date_value = request.query_params.get("date")
        try:
            date = datetime.date.fromisoformat(date_value) if date_value else self.today
        except ValueError:
            raise ValidationError({"date": ["Use the format YYYY-MM-DD."]})
        return Response(self.sheet(section, date))

    def post(self, request):
        serializer = SheetInputSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        section = self.get_section(serializer.validated_data["section"].pk)
        date = serializer.validated_data["date"]
        enrolled = {e.student_id for e in self.enrollments(section)}
        records = serializer.validated_data["records"]
        unknown = [r["student"] for r in records if r["student"] not in enrolled]
        if unknown:
            raise ValidationError({"records": ["Some students are not in this section."]})
        with transaction.atomic():
            for r in records:
                AttendanceRecord.objects.update_or_create(
                    student_id=r["student"],
                    date=date,
                    defaults={
                        "tenant": self.tenant,
                        "section": section,
                        "status": r["status"],
                        "remark": r["remark"],
                        "marked_by": request.user,
                    },
                )
        return Response(self.sheet(section, date))


class MonthlyReportView(AttendanceView):
    """Per-student totals and daily statuses for a section over one month."""

    def get(self, request):
        section = self.get_section(request.query_params.get("section"))
        first, last = parse_month(request.query_params.get("month"), self.today)
        enrollments = self.enrollments(section)
        records = AttendanceRecord.objects.filter(
            student__in=[e.student_id for e in enrollments], date__range=(first, last)
        ).values("student_id", "date", "status")
        by_student = {}
        days = set()
        for r in records:
            by_student.setdefault(r["student_id"], {})[r["date"].isoformat()] = r["status"]
            days.add(r["date"].isoformat())
        rows = []
        for e in enrollments:
            daily = by_student.get(e.student_id, {})
            rows.append(
                {
                    "student": e.student_id,
                    "full_name": e.student.full_name,
                    "admission_no": e.student.admission_no,
                    "roll_number": e.roll_number,
                    "summary": summarize(daily.values()),
                    "days": daily,
                }
            )
        return Response(
            {
                "section": section_label(section),
                "month": first.strftime("%Y-%m"),
                "days": sorted(days),
                "students": rows,
                "summary": summarize(s for row in rows for s in row["days"].values()),
            }
        )


def student_attendance(student, month):
    """Month records and summaries (month and current session) for one student."""
    today = tenant_today(student.tenant)
    first, last = parse_month(month, today)
    month_records = list(
        AttendanceRecord.objects.filter(student=student, date__range=(first, last)).values("date", "status", "remark")
    )
    session = current_session(student.tenant)
    session_statuses = []
    if session is not None:
        session_statuses = AttendanceRecord.objects.filter(
            student=student, date__range=(session.start_date, session.end_date)
        ).values_list("status", flat=True)
    today_status = AttendanceRecord.objects.filter(student=student, date=today).values_list("status", flat=True).first()
    return {
        "student": student.id,
        "full_name": student.full_name,
        "month": first.strftime("%Y-%m"),
        "records": month_records,
        "month_summary": summarize(r["status"] for r in month_records),
        "session_name": session.name if session else None,
        "session_summary": summarize(session_statuses),
        "today": today_status,
    }


class StudentAttendanceView(AttendanceView):
    """A student's attendance for admins and teachers."""

    def get(self, request, pk):
        student = get_object_or_404(Student, tenant=self.tenant, pk=pk)
        return Response(student_attendance(student, request.query_params.get("month")))


class TodayView(AttendanceView):
    """Today's attendance across the sections this user can see."""

    def get(self, request):
        session = current_session(self.tenant)
        today = self.today
        if session is None:
            return Response({"date": today, "sections": 0, "marked_sections": 0, "unmarked": [], "summary": summarize([])})
        sections = list(self.accessible_sections().filter(session=session, is_active=True))
        records = AttendanceRecord.objects.filter(tenant=self.tenant, date=today, section__in=sections)
        marked = set(records.values_list("section_id", flat=True).distinct())
        with_students = set(
            Enrollment.objects.filter(section__in=sections, student__status=StudentStatus.ACTIVE)
            .values_list("section_id", flat=True)
            .distinct()
        )
        unmarked = [
            section_label(s) for s in sorted(sections, key=lambda s: (s.program.sort_order, s.program.name, s.name))
            if s.id in with_students and s.id not in marked
        ]
        return Response(
            {
                "date": today,
                "sections": len(with_students),
                "marked_sections": len(marked),
                "unmarked": unmarked,
                "summary": summarize(records.values_list("status", flat=True)),
            }
        )


class MyAttendanceView(AttendanceView):
    """Parents see a child's attendance (``?student=``); students see their own."""

    allowed_roles = (Role.PARENT, Role.STUDENT)

    def get(self, request):
        user = request.user
        if user.role == Role.STUDENT:
            student = getattr(user, "student_profile", None)
        else:
            guardian = getattr(user, "guardian_profile", None)
            student = (
                guardian.students.filter(pk=request.query_params.get("student") or 0).first() if guardian else None
            )
        if student is None:
            raise NotFound("Student not found.")
        return Response(student_attendance(student, request.query_params.get("month")))



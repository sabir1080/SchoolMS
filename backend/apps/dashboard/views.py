"""One endpoint with everything the admin/teacher dashboard shows.

Teachers see their own sections only (where they are class teacher) and no fees.
Attendance and fees parts are included only when the plan has those features.
"""

import datetime
from collections import Counter, defaultdict
from decimal import Decimal

from django.db.models import Count, Sum
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.academics.models import Section
from apps.accounts.models import Role, User
from apps.attendance.models import AttendanceRecord, summarize
from apps.core.permissions import HasRole
from apps.core.timeutils import parse_month, tenant_today
from apps.fees.models import Invoice, InvoiceStatus, Payment
from apps.students.models import Enrollment, Student, StudentStatus
from apps.students.services import current_session
from apps.subscriptions.features import Feature
from apps.subscriptions.gating import ActiveSubscription, get_subscription

TREND_DAYS = 14
FEE_MONTHS = 6
LOW_ATTENDANCE = 75
LOW_ATTENDANCE_MIN_DAYS = 3


def summarize_counts(counts):
    """``summarize`` for a {status: count} mapping."""
    return summarize(status for status, n in counts.items() for _ in range(n))


def money(value):
    return f"{Decimal(value or 0):.2f}"


def previous_months(today, count):
    """['2026-05', ..., '2026-10'] ending with today's month."""
    months = []
    year, month = today.year, today.month
    for _ in range(count):
        months.append(f"{year}-{month:02d}")
        month -= 1
        if month == 0:
            year, month = year - 1, 12
    return list(reversed(months))


class DashboardView(APIView):
    def get_permissions(self):
        return [HasRole.for_roles(Role.ADMIN, Role.TEACHER)(), ActiveSubscription()]

    def get(self, request):
        tenant = request.user.tenant
        is_admin = request.user.role == Role.ADMIN
        plan = get_subscription(tenant).plan
        today = tenant_today(tenant)
        session = current_session(tenant)

        sections = Section.objects.filter(tenant=tenant, session=session, is_active=True) if session else Section.objects.none()
        if not is_admin:
            sections = sections.filter(class_teacher=request.user)
        enrollments = Enrollment.objects.filter(section__in=sections, student__status=StudentStatus.ACTIVE)

        data = {
            "today": today,
            "session_name": session.name if session else None,
            "counts": self.counts(tenant, is_admin, sections, enrollments, today),
            "students_by_program": self.students_by_program(enrollments),
        }
        if plan.has_feature(Feature.ATTENDANCE):
            data["attendance"] = self.attendance(tenant, sections, enrollments, today)
        if is_admin and plan.has_feature(Feature.FEES):
            data["fees"] = self.fees(tenant, today)
        return Response(data)

    def counts(self, tenant, is_admin, sections, enrollments, today):
        if is_admin:
            students = Student.objects.filter(tenant=tenant, status=StudentStatus.ACTIVE)
        else:
            students = Student.objects.filter(pk__in=enrollments.values("student_id"))
        return {
            "students": students.count(),
            "new_admissions_this_month": students.filter(admission_date__gte=today.replace(day=1)).count(),
            "teachers": User.objects.filter(tenant=tenant, role=Role.TEACHER, is_active=True).count(),
            "sections": sections.count(),
            "unassigned_students": (
                Student.objects.filter(tenant=tenant, status=StudentStatus.ACTIVE)
                .exclude(pk__in=Enrollment.objects.filter(section__in=sections).values("student_id"))
                .count()
                if is_admin
                else 0
            ),
        }

    def students_by_program(self, enrollments):
        rows = (
            enrollments.order_by().values("section__program_id", "section__program__name", "section__program__sort_order")
            .annotate(count=Count("id"))
            .order_by("section__program__sort_order", "section__program__name")
        )
        return [{"program": r["section__program_id"], "name": r["section__program__name"], "count": r["count"]} for r in rows]

    def attendance(self, tenant, sections, enrollments, today):
        # order_by(): drop the model's default ordering so it does not split the GROUP BY.
        records = AttendanceRecord.objects.filter(tenant=tenant, section__in=sections).order_by()

        today_counts = Counter(dict(records.filter(date=today).values_list("status").annotate(n=Count("id"))))
        with_students = set(enrollments.values_list("section_id", flat=True).distinct())
        marked = set(records.filter(date=today).values_list("section_id", flat=True).distinct())

        by_day = defaultdict(Counter)
        recent = records.filter(date__gte=today - datetime.timedelta(days=45), date__lte=today)
        for row in recent.values("date", "status").annotate(n=Count("id")):
            by_day[row["date"]][row["status"]] = row["n"]
        trend = [
            {"date": day, **summarize_counts(by_day[day])}
            for day in sorted(by_day)[-TREND_DAYS:]
        ]

        first, last = parse_month(None, today)
        month_counts = Counter(
            dict(records.filter(date__range=(first, last)).values_list("status").annotate(n=Count("id")))
        )

        per_student = defaultdict(Counter)
        month_rows = records.filter(date__range=(first, last), student__status=StudentStatus.ACTIVE)
        for row in month_rows.values("student_id", "status").annotate(n=Count("id")):
            per_student[row["student_id"]][row["status"]] = row["n"]
        low = []
        for student_id, counts in per_student.items():
            summary = summarize_counts(counts)
            counted = summary["total"] - summary["leave"]
            if counted >= LOW_ATTENDANCE_MIN_DAYS and summary["percentage"] < LOW_ATTENDANCE:
                low.append((student_id, summary))
        low.sort(key=lambda item: item[1]["percentage"])
        names = {
            e.student_id: e
            for e in enrollments.filter(student_id__in=[s for s, _ in low]).select_related("student", "section__program")
        }
        return {
            "today": summarize_counts(today_counts),
            "sections_with_students": len(with_students),
            "marked_sections": len(marked & with_students),
            "trend": trend,
            "month": summarize_counts(month_counts),
            "low_attendance_threshold": LOW_ATTENDANCE,
            "low_attendance": [
                {
                    "student": student_id,
                    "full_name": names[student_id].student.full_name if student_id in names else "",
                    "class_name": (
                        f"{names[student_id].section.program.name} - {names[student_id].section.name}"
                        if student_id in names
                        else None
                    ),
                    "percentage": summary["percentage"],
                    "absent": summary["absent"],
                    "days": summary["total"],
                }
                for student_id, summary in low[:10]
            ],
        }

    def fees(self, tenant, today):
        months = previous_months(today, FEE_MONTHS)
        invoices = Invoice.objects.filter(tenant=tenant).exclude(status=InvoiceStatus.CANCELLED).order_by()
        billed = dict(invoices.filter(period__in=months).values_list("period").annotate(s=Sum("total")))
        trend = []
        for month in months:
            first, last = parse_month(month, today)
            collected = Payment.objects.filter(tenant=tenant, date__range=(first, last)).aggregate(s=Sum("amount"))["s"]
            trend.append({"month": month, "billed": money(billed.get(month)), "collected": money(collected)})
        due = invoices.filter(status__in=[InvoiceStatus.UNPAID, InvoiceStatus.PARTIAL])
        outstanding = (due.aggregate(s=Sum("total"))["s"] or 0) - (due.aggregate(s=Sum("paid"))["s"] or 0)
        overdue = due.filter(due_date__lt=today)
        return {
            "this_month": trend[-1],
            "trend": trend,
            "outstanding": money(outstanding),
            "overdue_students": overdue.values("student_id").distinct().count(),
        }

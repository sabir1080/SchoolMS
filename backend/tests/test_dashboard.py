import datetime
from zoneinfo import ZoneInfo
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.academics.models import AcademicSession, Program, Section
from apps.accounts.models import Role
from apps.attendance.models import AttendanceRecord
from apps.fees.models import Invoice, InvoiceItem, Payment
from apps.students.models import Enrollment, Student

# The institute's day (Asia/Karachi), not the server's UTC day: they differ late in the evening.
TODAY = timezone.localdate(timezone=ZoneInfo("Asia/Karachi"))


def auth(api, user):
    api.force_authenticate(user)
    return api


@pytest.fixture
def school(school_a, make_user):
    session = AcademicSession.objects.create(
        tenant=school_a, name="Now", start_date=TODAY - datetime.timedelta(days=300),
        end_date=TODAY + datetime.timedelta(days=60), is_current=True,
    )
    sana = make_user("sana", Role.TEACHER, school_a)
    make_user("omar", Role.TEACHER, school_a)
    c5 = Program.objects.create(tenant=school_a, name="Class 5", sort_order=2)
    c1 = Program.objects.create(tenant=school_a, name="Class 1", sort_order=1)
    a = Section.objects.create(tenant=school_a, program=c5, session=session, name="A", class_teacher=sana)
    b = Section.objects.create(tenant=school_a, program=c1, session=session, name="A")
    kids = []
    for i, section in enumerate([a, a, a, b]):
        s = Student.objects.create(tenant=school_a, admission_no=str(i), first_name=f"Kid{i}", gender="male",
                                   admission_date=TODAY - datetime.timedelta(days=100))
        Enrollment.objects.create(tenant=school_a, student=s, section=section)
        kids.append(s)
    Student.objects.create(tenant=school_a, admission_no="new", first_name="New", gender="male", admission_date=TODAY)
    Student.objects.create(tenant=school_a, admission_no="old", first_name="Old", gender="male", status="left")
    return {"session": session, "sana": sana, "a": a, "b": b, "kids": kids}


def mark(tenant, student, section, date, status):
    AttendanceRecord.objects.create(tenant=tenant, student=student, section=section, date=date, status=status)


def test_counts_and_students_by_class(api, admin_a, school):
    body = auth(api, admin_a).get("/api/dashboard/").json()
    assert body["counts"] == {
        "students": 5, "new_admissions_this_month": 1, "teachers": 2, "sections": 2, "unassigned_students": 1,
    }
    assert body["students_by_program"] == [
        {"program": school["b"].program_id, "name": "Class 1", "count": 1},
        {"program": school["a"].program_id, "name": "Class 5", "count": 3},
    ]
    assert body["session_name"] == "Now"


def test_attendance_trend_today_and_low_attendance(api, admin_a, school, school_a):
    k = school["kids"]
    days = [TODAY - datetime.timedelta(days=n) for n in range(4, -1, -1)]
    days = [d for d in days if d.month == TODAY.month] or [TODAY]
    for d in days:
        mark(school_a, k[0], school["a"], d, "present")
        mark(school_a, k[1], school["a"], d, "absent")
        mark(school_a, k[2], school["a"], d, "leave")
    mark(school_a, k[3], school["b"], TODAY, "late")
    att = auth(api, admin_a).get("/api/dashboard/").json()["attendance"]
    assert att["today"] == {"present": 1, "absent": 1, "leave": 1, "late": 1, "total": 4, "percentage": 66.7}
    assert att["sections_with_students"] == 2
    assert att["marked_sections"] == 2
    assert [t["date"] for t in att["trend"]] == [d.isoformat() for d in days]
    assert all(t["total"] >= 3 for t in att["trend"])
    assert att["month"]["absent"] == len(days)
    if len(days) >= 3:
        assert [row["full_name"] for row in att["low_attendance"]] == ["Kid1"]  # leave-only Kid2 is not "low"
        assert att["low_attendance"][0]["percentage"] == 0.0
        assert att["low_attendance"][0]["class_name"] == "Class 5 - A"


def test_trend_is_limited_to_recent_days(api, admin_a, school, school_a):
    k = school["kids"]
    for n in range(20):
        mark(school_a, k[0], school["a"], TODAY - datetime.timedelta(days=n), "present")
    trend = auth(api, admin_a).get("/api/dashboard/").json()["attendance"]["trend"]
    assert len(trend) == 14
    assert trend[-1]["date"] == TODAY.isoformat()


def test_teacher_sees_only_own_sections_and_no_fees(api, school, school_a):
    mark(school_a, school["kids"][3], school["b"], TODAY, "absent")  # not Sana's section
    mark(school_a, school["kids"][0], school["a"], TODAY, "present")
    body = auth(api, school["sana"]).get("/api/dashboard/").json()
    assert body["counts"]["students"] == 3
    assert body["counts"]["sections"] == 1
    assert body["counts"]["unassigned_students"] == 0
    assert [p["name"] for p in body["students_by_program"]] == ["Class 5"]
    assert body["attendance"]["today"]["absent"] == 0
    assert "fees" not in body


def test_fees_trend(api, admin_a, school, school_a):
    month = TODAY.strftime("%Y-%m")
    k = school["kids"]
    inv = Invoice.objects.create(
        tenant=school_a, number=1, student=k[0], session=school["session"], period=month, title="x",
        issue_date=TODAY, due_date=TODAY - datetime.timedelta(days=1), total=Decimal("3000"),
    )
    Invoice.objects.create(
        tenant=school_a, number=2, student=k[1], session=school["session"], period=month, title="x",
        issue_date=TODAY, due_date=TODAY + datetime.timedelta(days=5), total=Decimal("2000"),
    )
    Invoice.objects.create(
        tenant=school_a, number=3, student=k[2], session=school["session"], period=month, title="x",
        issue_date=TODAY, due_date=TODAY, total=Decimal("9999"), status="cancelled",
    )
    for invoice in Invoice.objects.all():
        InvoiceItem.objects.create(invoice=invoice, description="Tuition", amount=invoice.total)
    Payment.objects.create(tenant=school_a, receipt_number=1, invoice=inv, amount=Decimal("1000"), date=TODAY)
    for invoice in Invoice.objects.all():
        invoice.refresh_totals()
    fees = auth(api, admin_a).get("/api/dashboard/").json()["fees"]
    assert len(fees["trend"]) == 6
    assert fees["this_month"] == {"month": month, "billed": "5000.00", "collected": "1000.00"}
    assert fees["outstanding"] == "4000.00"
    assert fees["overdue_students"] == 1


def test_parts_follow_plan_features(api, admin_a, school, school_a):
    plan = school_a.subscription.plan
    plan.features = ["academics", "students"]
    plan.save()
    body = auth(api, admin_a).get("/api/dashboard/").json()
    assert "attendance" not in body and "fees" not in body


def test_no_current_session(api, admin_a, school):
    school["session"].is_current = False
    school["session"].save()
    body = auth(api, admin_a).get("/api/dashboard/").json()
    assert body["session_name"] is None
    assert body["counts"]["sections"] == 0
    assert body["students_by_program"] == []


def test_access(api, make_user, school, school_a):
    parent = make_user("p", Role.PARENT, school_a)
    assert auth(api, parent).get("/api/dashboard/").status_code == 403
    sub = school_a.subscription
    sub.current_period_end = timezone.now() - datetime.timedelta(days=1)
    sub.save()
    assert auth(api, school["sana"]).get("/api/dashboard/").status_code == 402


def test_isolated_per_institute(api, admin_b, school):
    body = auth(api, admin_b).get("/api/dashboard/").json()
    assert body["counts"]["students"] == 0

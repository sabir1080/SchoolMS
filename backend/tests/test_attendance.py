import datetime

import pytest
from django.utils import timezone

from apps.academics.models import AcademicSession, Program, Section
from apps.accounts.models import Role
from apps.attendance.models import AttendanceRecord, summarize
from apps.students.models import Enrollment, Guardian, Student, StudentGuardian

TODAY = timezone.localdate()


def auth(api, user):
    api.force_authenticate(user)
    return api


@pytest.fixture
def school(school_a, make_user):
    session = AcademicSession.objects.create(
        tenant=school_a, name="Now", start_date=TODAY - datetime.timedelta(days=200),
        end_date=TODAY + datetime.timedelta(days=100), is_current=True,
    )
    teacher = make_user("sana", Role.TEACHER, school_a, first_name="Sana")
    other_teacher = make_user("omar", Role.TEACHER, school_a)
    program = Program.objects.create(tenant=school_a, name="Class 5")
    a = Section.objects.create(tenant=school_a, program=program, session=session, name="A", class_teacher=teacher)
    b = Section.objects.create(tenant=school_a, program=program, session=session, name="B", class_teacher=other_teacher)
    students = []
    for roll, name in [("10", "Zain"), ("2", "Ali"), ("", "Bilal")]:
        s = Student.objects.create(tenant=school_a, admission_no=name, first_name=name, gender="male")
        Enrollment.objects.create(tenant=school_a, student=s, section=a, roll_number=roll)
        students.append(s)
    left = Student.objects.create(tenant=school_a, admission_no="L", first_name="Gone", gender="male", status="left")
    Enrollment.objects.create(tenant=school_a, student=left, section=a)
    in_b = Student.objects.create(tenant=school_a, admission_no="B1", first_name="Bee", gender="female")
    Enrollment.objects.create(tenant=school_a, student=in_b, section=b)
    zain, ali, bilal = students
    return {"session": session, "teacher": teacher, "a": a, "b": b, "zain": zain, "ali": ali, "bilal": bilal, "in_b": in_b}


def save(api, section, records, date=None):
    return api.post(
        "/api/attendance/sheet/",
        {"section": section.pk, "date": (date or TODAY).isoformat(), "records": records},
        format="json",
    )


def test_summarize():
    assert summarize(["present", "late", "absent", "leave"]) == {
        "present": 1, "absent": 1, "leave": 1, "late": 1, "total": 4, "percentage": 50.0,
    }
    assert summarize([])["percentage"] is None


def test_sheet_lists_active_students_in_roll_order(api, school):
    res = auth(api, school["teacher"]).get(f"/api/attendance/sheet/?section={school['a'].pk}")
    assert res.status_code == 200, res.json()
    body = res.json()
    assert [s["full_name"] for s in body["students"]] == ["Ali", "Zain", "Bilal"]  # 2, 10, then no roll
    assert body["marked"] is False
    assert all(s["status"] is None for s in body["students"])


def test_teacher_marks_and_updates_attendance(api, school):
    api = auth(api, school["teacher"])
    z, a, b = school["zain"], school["ali"], school["bilal"]
    res = save(api, school["a"], [
        {"student": z.pk, "status": "present"},
        {"student": a.pk, "status": "absent"},
        {"student": b.pk, "status": "late", "remark": "Bus late"},
    ])
    assert res.status_code == 200, res.json()
    body = res.json()
    assert body["marked"] is True
    assert body["summary"]["present"] == 1
    assert body["summary"]["percentage"] == pytest.approx(66.7)
    # Update: Ali was actually on leave.
    res = save(api, school["a"], [{"student": a.pk, "status": "leave"}])
    assert res.status_code == 200
    assert AttendanceRecord.objects.count() == 3
    assert AttendanceRecord.objects.get(student=a).status == "leave"
    assert AttendanceRecord.objects.get(student=b).remark == "Bus late"
    assert AttendanceRecord.objects.get(student=z).marked_by == school["teacher"]


def test_teacher_only_for_own_section(api, school):
    api = auth(api, school["teacher"])
    assert api.get(f"/api/attendance/sheet/?section={school['b'].pk}").status_code == 403
    assert save(api, school["b"], [{"student": school["in_b"].pk, "status": "present"}]).status_code == 403
    sections = api.get("/api/attendance/sections/").json()
    assert [s["name"] for s in sections] == ["A"]
    assert sections[0]["student_count"] == 3


def test_admin_can_mark_any_section(api, admin_a, school):
    api = auth(api, admin_a)
    assert save(api, school["b"], [{"student": school["in_b"].pk, "status": "present"}]).status_code == 200
    sections = api.get("/api/attendance/sections/").json()
    assert {s["name"]: s["marked_today"] for s in sections} == {"A": False, "B": True}


def test_rejects_future_dates_and_dates_outside_session(api, school):
    api = auth(api, school["teacher"])
    rec = [{"student": school["ali"].pk, "status": "present"}]
    res = save(api, school["a"], rec, TODAY + datetime.timedelta(days=1))
    assert res.status_code == 400
    assert "future" in res.json()["date"][0]
    res = save(api, school["a"], rec, TODAY - datetime.timedelta(days=400))
    assert res.status_code == 400
    assert "within the session" in res.json()["date"][0]


def test_rejects_students_not_in_section_and_duplicates(api, school):
    api = auth(api, school["teacher"])
    res = save(api, school["a"], [{"student": school["in_b"].pk, "status": "present"}])
    assert res.status_code == 400
    res = save(api, school["a"], [{"student": school["ali"].pk, "status": "present"}] * 2)
    assert res.status_code == 400
    assert AttendanceRecord.objects.count() == 0


def test_other_institute_cannot_access(api, admin_b, school):
    res = auth(api, admin_b).get(f"/api/attendance/sheet/?section={school['a'].pk}")
    assert res.status_code == 404


def test_monthly_report(api, school, admin_a):
    api = auth(api, school["teacher"])
    d1 = TODAY.replace(day=1)
    days = [d1 + datetime.timedelta(days=i) for i in range(3) if d1 + datetime.timedelta(days=i) <= TODAY]
    for d in days:
        save(api, school["a"], [
            {"student": school["ali"].pk, "status": "present"},
            {"student": school["zain"].pk, "status": "absent"},
        ], d)
    res = api.get(f"/api/attendance/report/?section={school['a'].pk}&month={TODAY:%Y-%m}")
    assert res.status_code == 200, res.json()
    body = res.json()
    assert body["days"] == [d.isoformat() for d in days]
    rows = {r["full_name"]: r for r in body["students"]}
    assert rows["Ali"]["summary"]["present"] == len(days)
    assert rows["Ali"]["summary"]["percentage"] == 100.0
    assert rows["Zain"]["summary"]["percentage"] == 0.0
    assert rows["Bilal"]["summary"]["total"] == 0
    assert api.get(f"/api/attendance/report/?section={school['a'].pk}&month=bad").status_code == 400


def test_today_summary(api, admin_a, school):
    save(auth(api, school["teacher"]), school["a"], [
        {"student": school["ali"].pk, "status": "present"},
        {"student": school["zain"].pk, "status": "absent"},
    ])
    body = auth(api, admin_a).get("/api/attendance/today/").json()
    assert body["sections"] == 2
    assert body["marked_sections"] == 1
    assert [s["name"] for s in body["unmarked"]] == ["B"]
    assert body["summary"]["present"] == 1
    assert body["summary"]["absent"] == 1


def test_student_attendance_for_staff(api, admin_a, school):
    save(auth(api, school["teacher"]), school["a"], [{"student": school["ali"].pk, "status": "late"}])
    body = auth(api, admin_a).get(f"/api/attendance/students/{school['ali'].pk}/").json()
    assert body["today"] == "late"
    assert body["month_summary"]["late"] == 1
    assert body["session_summary"]["percentage"] == 100.0


def test_parent_and_student_portal(api, school, school_a, make_user):
    save(auth(api, school["teacher"]), school["a"], [
        {"student": school["ali"].pk, "status": "present"},
        {"student": school["zain"].pk, "status": "absent"},
    ])
    parent = make_user("raza", Role.PARENT, school_a)
    guardian = Guardian.objects.create(tenant=school_a, name="Raza", user=parent)
    StudentGuardian.objects.create(student=school["ali"], guardian=guardian)
    api = auth(api, parent)
    res = api.get(f"/api/me/attendance/?student={school['ali'].pk}")
    assert res.status_code == 200
    assert res.json()["today"] == "present"
    # Not their child:
    assert api.get(f"/api/me/attendance/?student={school['zain'].pk}").status_code == 404
    assert api.get(f"/api/attendance/sheet/?section={school['a'].pk}").status_code == 403

    kid = make_user("zain", Role.STUDENT, school_a)
    school["zain"].user = kid
    school["zain"].save()
    res = auth(api, kid).get("/api/me/attendance/")
    assert res.json()["today"] == "absent"


def test_student_with_attendance_cannot_be_deleted(api, admin_a, school):
    save(auth(api, school["teacher"]), school["a"], [{"student": school["ali"].pk, "status": "present"}])
    res = auth(api, admin_a).delete(f"/api/students/{school['ali'].pk}/")
    assert res.status_code == 400
    assert "Mark them as Left" in res.json()[0]


def test_plan_without_attendance(api, school, school_a):
    plan = school_a.subscription.plan
    plan.features = [f for f in plan.features if f != "attendance"]
    plan.save()
    assert auth(api, school["teacher"]).get("/api/attendance/sections/").status_code == 402


def test_today_uses_institute_timezone(school_a):
    from apps.core.timeutils import tenant_today

    school_a.timezone = "Pacific/Kiritimati"  # UTC+14
    assert tenant_today(school_a) >= timezone.localdate()
    school_a.timezone = "Not/AZone"
    assert tenant_today(school_a) == timezone.localdate()

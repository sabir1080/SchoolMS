import datetime

from django.core.management import call_command

from apps.accounts.models import Role, User
from apps.attendance.models import AttendanceRecord
from apps.exams.models import CombinedResult, Exam, Mark
from apps.fees.models import Invoice, Payment
from apps.students.models import Student
from apps.subscriptions.models import Plan
from apps.tenants.demo import seed_demo, wipe_institutes
from apps.tenants.models import Tenant

TODAY = datetime.date(2026, 10, 27)


def test_seed_demo_builds_a_complete_school(db, api):
    tenant = seed_demo(today=TODAY)
    assert tenant.subscription.is_usable and tenant.subscription.status == "active"
    from apps.agreements.models import SignedAgreement

    assert SignedAgreement.objects.get(tenant=tenant).status == "active"
    brand = api.get("/api/public/institutes/demo/").json()["brand"]
    assert brand["color"] == "blue" and brand["logo"].startswith("data:image/png;base64,")
    assert Student.objects.filter(tenant=tenant).count() == 32
    assert set(User.objects.filter(tenant=tenant).values_list("username", flat=True)) >= {"admin", "sana", "rashid", "ahmed"}
    assert AttendanceRecord.objects.filter(tenant=tenant).count() > 1000
    assert Invoice.objects.filter(tenant=tenant).values("period").distinct().count() == 6
    assert Invoice.objects.filter(tenant=tenant, status="unpaid").exists()
    assert Payment.objects.filter(tenant=tenant).count() > 100
    assert list(Exam.objects.filter(tenant=tenant).order_by("start_date").values_list("status", flat=True)) == [
        "published", "marks_open", "draft", "draft"
    ]
    annual = CombinedResult.objects.get(tenant=tenant)
    assert [str(c.weight) for c in annual.components.all()] == ["25.00", "25.00", "50.00"]
    assert Mark.objects.filter(tenant=tenant).count() > 200
    from apps.homework.models import Homework
    from apps.messaging.models import Message
    from apps.payroll.models import Payslip
    from apps.timetable.models import TimetableEntry

    assert TimetableEntry.objects.filter(tenant=tenant).count() == 4 * 5 * 7
    assert Homework.objects.filter(tenant=tenant).count() == 4 * 5 * 2
    assert Payslip.objects.filter(tenant=tenant, status="paid").exists() and Payslip.objects.filter(tenant=tenant, status="unpaid").exists()
    assert Message.objects.filter(tenant=tenant, kind="fee").exists()
    # Logins work and the parent sees both children
    res = api.post("/api/auth/login/", {"institute_code": "demo", "username": "rashid", "password": "demo1234"}, format="json")
    assert res.status_code == 200, res.json()
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {res.json()['access']}")
    children = api.get("/api/me/children/").json()
    assert {c["full_name"] for c in children} == {"Ahmed Rashid", "Fatima Rashid"}


def test_seed_twice_replaces_demo_and_wipe_keeps_platform(db, make_tenant, super_admin):
    seed_demo(today=TODAY)
    seed_demo(today=TODAY)  # the old demo (with marks, payments, attendance) is deleted first
    assert Tenant.objects.filter(slug="demo").count() == 1
    make_tenant("other")
    call_command("seed_demo", "--wipe-all")
    assert list(Tenant.objects.values_list("slug", flat=True)) == ["demo"]
    wipe_institutes()
    assert Tenant.objects.count() == 0 and Student.objects.count() == 0 and Mark.objects.count() == 0
    assert User.objects.filter(role=Role.SUPER_ADMIN).exists() or User.objects.filter(is_superuser=True).exists()
    assert Plan.objects.count() == 3


def test_scholars_school_nursery_to_class_3_with_photos(db, api):
    from apps.academics.models import Section
    from apps.students.models import Enrollment
    from apps.tenants.demo import SCHOLARS, seed_school

    seed_demo(today=TODAY)
    tenant = seed_school(SCHOLARS, today=TODAY)
    assert tenant.slug == "scholars" and tenant.subscription.is_usable
    assert Tenant.objects.filter(slug="demo").exists()  # the other demo school is left alone
    sections = Section.objects.filter(tenant=tenant)
    assert sorted(f"{s.program.name} {s.name}" for s in sections) == sorted(
        f"{c} {s}" for c in ["Nursery", "Prep", "Class 1", "Class 2", "Class 3"] for s in "AB"
    )
    for section in sections:
        assert 18 <= Enrollment.objects.filter(section=section).count() <= 21
    students = Student.objects.filter(tenant=tenant)
    assert students.count() == 201
    assert all(s.photo.startswith("data:image/jpeg;base64,") and len(s.photo) < 140_000 for s in students)
    # Every student in a class has a different photo, and the photos match the class's age group
    for section in sections:
        photos = list(Student.objects.filter(enrollments__section__program=section.program).values_list("photo", flat=True))
        assert len(set(photos)) == len(photos)
    ages = {
        name: {TODAY.year - d.year for d in Student.objects.filter(
            tenant=tenant, enrollments__section__program__name=name).values_list("date_of_birth", flat=True)}
        for name in ["Nursery", "Class 3"]
    }
    assert ages == {"Nursery": {4}, "Class 3": {8}}
    assert Invoice.objects.filter(tenant=tenant).values("period").distinct().count() == 6
    assert Mark.objects.filter(tenant=tenant).count() > 1000
    assert AttendanceRecord.objects.filter(tenant=tenant).count() > 5000
    # Logins: admin, class teacher, parent with two children, student; the student's photo is on the ID card
    for username in ["admin", "teacher", "parent", "student", "rabia"]:
        res = api.post("/api/auth/login/", {"institute_code": "scholars", "username": username, "password": "demo1234"}, format="json")
        assert res.status_code == 200, (username, res.json())
    res = api.post("/api/auth/login/", {"institute_code": "scholars", "username": "parent", "password": "demo1234"}, format="json")
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {res.json()['access']}")
    assert {c["full_name"] for c in api.get("/api/me/children/").json()} == {"Hamza Siddiqui", "Anaya Siddiqui"}
    call_command("seed_demo", "--school", "scholars")
    assert Tenant.objects.filter(slug="scholars").count() == 1 and Tenant.objects.filter(slug="demo").exists()

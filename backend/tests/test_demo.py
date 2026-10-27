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

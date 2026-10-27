import datetime

from django.utils import timezone

from apps.accounts.models import Role
from apps.students.models import Student
from apps.subscriptions.models import Plan
from apps.subscriptions.services import record_payment


def test_overview_counts_revenue_and_renewals(api, super_admin, make_tenant, make_user):
    alpha, beta, gamma, delta = (make_tenant(s) for s in ("alpha", "beta", "gamma", "delta"))
    pro = Plan.objects.get(code="pro")
    record_payment(alpha.subscription, plan=pro, billing_cycle="monthly", amount=5000, currency="PKR", method="cash")
    record_payment(beta.subscription, plan=Plan.objects.get(code="basic"), billing_cycle="monthly", amount=2500, currency="PKR", method="bank_transfer")
    # gamma's trial ends in 3 days; delta expired; a suspended institute is counted apart.
    gamma.subscription.current_period_end = timezone.now() + datetime.timedelta(days=3)
    gamma.subscription.save()
    delta.subscription.current_period_end = timezone.now() - datetime.timedelta(days=1)
    delta.subscription.save()
    make_tenant("eps").__class__.objects.filter(slug="eps").update(is_active=False)
    for i in range(3):
        Student.objects.create(tenant=alpha, admission_no=str(i), first_name=f"S{i}", gender="male")
    Student.objects.create(tenant=beta, admission_no="1", first_name="B", gender="male")
    make_user("a1", Role.ADMIN, alpha)

    api.force_authenticate(super_admin)
    body = api.get("/api/platform/overview/").json()
    assert body["institutes"] == {"total": 5, "active": 3, "trial": 1, "paying": 2, "expired": 1, "suspended": 1, "new_this_month": 5}
    assert {p["plan"]: p["institutes"] for p in body["plans"]} == {"Pro": 2, "Basic": 1}
    assert body["students"] == 4 and body["users"] == 1
    pkr = body["revenue"][0]
    assert (pkr["currency"], pkr["this_month"], pkr["this_year"]) == ("PKR", "7500.00", "7500.00")
    assert len(pkr["months"]) == 6 and pkr["months"][-1]["amount"] == "7500.00"
    assert [e["slug"] for e in body["expiring"]] == ["gamma"] and body["expiring"][0]["days_left"] == 3
    assert [e["slug"] for e in body["expired"]] == ["delta"]
    assert body["recent_payments"][0]["amount"] in ("5000.00", "2500.00")
    assert body["top_institutes"][0] == {"tenant_id": alpha.id, "tenant__name": "Alpha", "students": 3}


def test_overview_is_for_super_admins_only(api, admin_a):
    api.force_authenticate(admin_a)
    assert api.get("/api/platform/overview/").status_code == 403
    api.force_authenticate(None)
    assert api.get("/api/platform/overview/").status_code == 401

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.subscriptions.gating import ActiveSubscription, RequiresFeature
from apps.subscriptions.models import Plan, SubscriptionStatus
from apps.tenants.models import Tenant

REGISTRATION = {
    "name": "Bright Future Academy",
    "slug": "Bright-Future",
    "institute_type": "coaching",
    "country": "pk",
    "currency": "pkr",
    "timezone": "Asia/Karachi",
    "admin_username": "principal",
    "admin_email": "Principal@Bright.test",
    "admin_password": "Str0ng-pass-123",
    "admin_first_name": "Sara",
}


def auth(api, user):
    api.force_authenticate(user)
    return api


def expire(tenant):
    sub = tenant.subscription
    sub.current_period_end = timezone.now() - timedelta(minutes=1)
    sub.save()


# --- Plans -----------------------------------------------------------------

def test_default_plans_are_seeded(api, db):
    res = api.get("/api/public/plans/")
    assert res.status_code == 200
    plans = res.json()
    assert [p["code"] for p in plans] == ["basic", "pro", "enterprise"]
    pro = plans[1]
    assert {"currency": "PKR", "billing_cycle": "monthly", "amount": "7000.00"} in pro["prices"]
    assert "Attendance" in pro["feature_labels"]
    assert plans[2]["max_students"] is None


# --- Self registration -------------------------------------------------------

def test_registration_creates_institute_admin_trial_and_logs_in(api, db):
    res = api.post("/api/public/register/", REGISTRATION, format="json")
    assert res.status_code == 201, res.json()
    body = res.json()
    assert body["access"] and body["refresh"]
    assert body["user"]["role"] == Role.ADMIN
    assert body["user"]["tenant"]["slug"] == "bright-future"
    assert body["user"]["tenant"]["currency"] == "PKR"

    tenant = Tenant.objects.get(slug="bright-future")
    sub = tenant.subscription
    assert sub.status == SubscriptionStatus.TRIALING
    assert sub.plan.code == "pro"
    assert sub.days_left == 14
    assert User.objects.get(tenant=tenant).email == "principal@bright.test"


def test_registration_allows_blank_optional_fields(api, db):
    res = api.post(
        "/api/public/register/",
        {**REGISTRATION, "admin_first_name": "", "admin_last_name": "", "phone": ""},
        format="json",
    )
    assert res.status_code == 201, res.json()


def test_registration_rejects_taken_reserved_and_bad_codes(api, school_a):
    for code in ("alpha", "admin", "a", "bad code", "-x-"):
        res = api.post("/api/public/register/", {**REGISTRATION, "slug": code}, format="json")
        assert res.status_code == 400, code
        assert "slug" in res.json()


def test_registration_rejects_too_short_password(api, db):
    res = api.post("/api/public/register/", {**REGISTRATION, "admin_password": "123"}, format="json")
    assert res.status_code == 400
    assert "admin_password" in res.json()
    assert not Tenant.objects.exists()


def test_registration_cannot_create_suspended_or_extra_fields(api, db):
    res = api.post("/api/public/register/", {**REGISTRATION, "is_active": False}, format="json")
    assert res.status_code == 201
    assert Tenant.objects.get().is_active is True


# --- Subscription status ---------------------------------------------------

def test_my_subscription_shows_plan_days_and_usage(api, admin_a, make_user, school_a):
    from apps.students.models import Student

    Student.objects.create(tenant=school_a, admission_no="1", first_name="Ali", gender="male")
    Student.objects.create(tenant=school_a, admission_no="2", first_name="Old", gender="male", status="left")
    make_user("s1", Role.STUDENT, school_a)  # a login is not an admission
    make_user("t1", Role.TEACHER, school_a)
    res = auth(api, admin_a).get("/api/subscription/")
    assert res.status_code == 200
    body = res.json()
    assert body["effective_status"] == "trialing"
    assert body["is_usable"] is True
    assert body["plan"]["code"] == "pro"
    assert body["usage"] == {"students": 1, "staff": 2}


def test_expired_subscription_blocks_modules_but_not_billing(api, admin_a, school_a):
    expire(school_a)
    api = auth(api, admin_a)
    res = api.get("/api/users/")
    assert res.status_code == 402
    assert res.json()["detail"].startswith("Your institute's subscription has expired")
    sub = api.get("/api/subscription/")
    assert sub.status_code == 200
    assert sub.json()["effective_status"] == "expired"
    assert api.get("/api/auth/me/").status_code == 200


def test_limit_on_staff(api, admin_a, school_a):
    plan = school_a.subscription.plan
    plan.max_staff = 2
    plan.save()
    api = auth(api, admin_a)

    def add(username, role):
        return api.post("/api/users/", {"username": username, "password": "Str0ng-pass-123", "role": role}, format="json")

    assert add("t1", "teacher").status_code == 201  # admin_a + t1 = 2 staff
    res = add("t2", "teacher")
    assert res.status_code == 402
    assert "allows up to 2" in res.json()["detail"]
    assert add("p1", "parent").status_code == 201  # parents are not limited
    assert add("s1", "student").status_code == 201  # student logins are not limited here

    # Deactivating frees a seat; reactivating is checked again.
    t1 = User.objects.get(username="t1")
    assert api.delete(f"/api/users/{t1.pk}/").status_code == 204
    assert add("t2", "teacher").status_code == 201
    assert api.patch(f"/api/users/{t1.pk}/", {"is_active": True}, format="json").status_code == 402
    # Switching a parent to teacher is checked too.
    p1 = User.objects.get(username="p1")
    assert api.patch(f"/api/users/{p1.pk}/", {"role": "teacher"}, format="json").status_code == 402
    # Editing an already-counted user is fine.
    t2 = User.objects.get(username="t2")
    assert api.patch(f"/api/users/{t2.pk}/", {"first_name": "X"}, format="json").status_code == 200


def test_feature_gating(rf, admin_a, school_a):
    request = rf.get("/")
    request.user = admin_a

    class View:
        required_feature = "white_label"

    with pytest.raises(Exception) as exc:
        RequiresFeature().has_permission(request, View())
    assert exc.value.status_code == 402
    assert exc.value.get_codes() == "feature_not_in_plan"

    View.required_feature = "attendance"
    assert RequiresFeature().has_permission(request, View()) is True
    assert ActiveSubscription().has_permission(request, View()) is True


# --- Platform management ---------------------------------------------------

def test_super_admin_records_payment_and_extends(api, super_admin, school_a):
    expire(school_a)
    api = auth(api, super_admin)
    res = api.post(
        f"/api/platform/tenants/{school_a.pk}/record-payment/",
        {"plan": "basic", "billing_cycle": "monthly", "amount": "3000", "currency": "pkr", "method": "jazzcash",
         "reference": "TX123"},
        format="json",
    )
    assert res.status_code == 200, res.json()
    sub = res.json()["subscription"]
    assert sub["plan"]["code"] == "basic"
    assert sub["status"] == "active"
    assert sub["days_left"] == 30

    payments = api.get(f"/api/platform/tenants/{school_a.pk}/payments/").json()
    assert payments[0]["amount"] == "3000.00"
    assert payments[0]["currency"] == "PKR"
    assert payments[0]["method"] == "jazzcash"


def test_payment_during_trial_starts_after_trial(api, super_admin, school_a):
    trial_end = school_a.subscription.current_period_end
    auth(api, super_admin).post(
        f"/api/platform/tenants/{school_a.pk}/record-payment/",
        {"plan": "pro", "billing_cycle": "yearly", "amount": "350", "currency": "USD", "method": "card"},
        format="json",
    )
    school_a.subscription.refresh_from_db()
    assert school_a.subscription.current_period_end == trial_end + timedelta(days=365)


def test_super_admin_can_change_subscription_directly(api, super_admin, school_a):
    res = auth(api, super_admin).patch(
        f"/api/platform/tenants/{school_a.pk}/subscription/",
        {"plan": "enterprise", "status": "cancelled"},
        format="json",
    )
    assert res.status_code == 200
    assert res.json()["subscription"]["plan"]["code"] == "enterprise"
    assert res.json()["subscription"]["effective_status"] == "cancelled"


def test_institute_admin_cannot_manage_subscriptions(api, admin_a, school_a):
    res = auth(api, admin_a).post(
        f"/api/platform/tenants/{school_a.pk}/record-payment/",
        {"plan": "enterprise", "billing_cycle": "yearly", "amount": "0", "currency": "PKR", "method": "cash"},
        format="json",
    )
    assert res.status_code == 403
    assert Plan.objects.get(code="pro") == school_a.subscription.plan

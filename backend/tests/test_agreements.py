import datetime

from django.utils import timezone

from apps.accounts.models import Role
from apps.agreements.models import ProviderProfile, SignedAgreement
from tests.test_subscriptions import REGISTRATION

SIGN = {
    "plan": "pro", "billing_cycle": "yearly", "institute_legal_name": "Alpha School (Pvt) Ltd",
    "institute_address": "12 Mall Road, Lahore", "signer_name": "Farhan Ahmed", "signer_designation": "Principal",
    "signer_cnic": "3520212345671", "signer_phone": "0300-1234567", "signature": "farhan  ahmed", "accept": True,
}


def test_registration_needs_and_records_the_trial_agreement(api, db):
    no = api.post("/api/public/register/", {**REGISTRATION, "accept_terms": False}, format="json")
    assert no.status_code == 400 and "accept_terms" in no.json()
    preview = api.get("/api/public/agreements/trial/").json()
    assert preview["version"] and preview["sections"][0]["heading"] == "1. The free trial" and "14 days" in preview["sections"][0]["body"]
    res = api.post("/api/public/register/", REGISTRATION, format="json", HTTP_X_FORWARDED_FOR="203.0.113.9, 10.0.0.1")
    assert res.status_code == 201
    agreement = SignedAgreement.objects.get()
    assert (agreement.kind, agreement.status, agreement.signer_name, agreement.ip_address) == ("trial", "accepted", "Sara", "203.0.113.9")
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {res.json()['access']}")
    listed = api.get("/api/agreements/").json()
    assert [a["kind"] for a in listed] == ["trial"] and listed[0]["number"].startswith("AGR-")


def test_sign_pay_and_activate(api, admin_a, super_admin, school_a):
    ProviderProfile.objects.create(business_name="EduSoft Pakistan", payment_instructions="Meezan Bank 0101-123", grace_days=5)
    api.force_authenticate(admin_a)
    preview = api.get("/api/agreements/preview/?plan=pro&cycle=yearly").json()
    assert preview["schedule"]["plan"] == "Pro" and preview["schedule"]["price"] == "PKR 70,000"
    assert preview["provider"]["business_name"] == "EduSoft Pakistan" and "5 days" in preview["sections"][2]["body"]
    assert preview["prefill"]["institute_legal_name"] == "Alpha" and preview["renewal"] is False
    assert preview["payment_instructions"] == "Meezan Bank 0101-123"

    assert "signer_cnic" in api.post("/api/agreements/", {**SIGN, "signer_cnic": "123"}, format="json").json()
    assert "signature" in api.post("/api/agreements/", {**SIGN, "signature": "Someone Else"}, format="json").json()
    assert "accept" in api.post("/api/agreements/", {**SIGN, "accept": False}, format="json").json()
    signed = api.post("/api/agreements/", SIGN, format="json").json()
    assert signed["status"] == "pending_payment" and signed["signer_cnic"] == "35202-1234567-1"
    assert signed["amount"] == "70000.00" and signed["schedule"]["cycle_label"] == "Yearly (365 days)"
    api.post(f"/api/agreements/{signed['id']}/", {"payment_reference": "MZN-778"}, format="json")
    detail = api.get(f"/api/agreements/{signed['id']}/").json()
    assert detail["payment_reference"] == "MZN-778" and detail["payment_instructions"] == "Meezan Bank 0101-123"

    # Signing again replaces the unpaid one.
    second = api.post("/api/agreements/", {**SIGN, "billing_cycle": "monthly"}, format="json").json()
    assert SignedAgreement.objects.get(pk=signed["id"]).status == "cancelled"

    api.force_authenticate(super_admin)
    overview = api.get("/api/platform/overview/").json()
    assert [p["number"] for p in overview["pending_agreements"]] == [second["number"]]
    res = api.post(f"/api/platform/tenants/{school_a.pk}/record-payment/",
                   {"plan": "pro", "billing_cycle": "monthly", "amount": "7000", "currency": "PKR", "method": "bank_transfer"}, format="json")
    assert res.status_code == 200 and res.json()["agreement"] == second["id"]
    active = SignedAgreement.objects.get(pk=second["id"])
    assert active.status == "active" and active.payment.amount == 7000
    assert (active.period_end - active.period_start) == datetime.timedelta(days=30)
    assert active.period_end > timezone.now() + datetime.timedelta(days=29)
    assert api.get("/api/platform/overview/").json()["pending_agreements"] == []

    # Renewal: details come from the last agreement; the new one replaces the active one once paid.
    api.force_authenticate(admin_a)
    again = api.get("/api/agreements/preview/?plan=pro&cycle=monthly").json()
    assert again["renewal"] is True and again["prefill"]["signer_cnic"] == "35202-1234567-1"
    third = api.post("/api/agreements/", {**SIGN, "billing_cycle": "monthly"}, format="json").json()
    api.force_authenticate(super_admin)
    api.post(f"/api/platform/tenants/{school_a.pk}/record-payment/",
             {"plan": "pro", "billing_cycle": "monthly", "amount": "7000", "currency": "PKR", "method": "cash", "agreement": third["id"]}, format="json")
    assert SignedAgreement.objects.get(pk=second["id"]).status == "superseded"
    assert SignedAgreement.objects.get(pk=third["id"]).status == "active"
    assert len(api.get(f"/api/platform/agreements/?tenant={school_a.pk}").json()) == 3


def test_agreement_text_is_frozen_when_signed(api, admin_a):
    api.force_authenticate(admin_a)
    signed = api.post("/api/agreements/", SIGN, format="json").json()
    profile = ProviderProfile.get()
    profile.business_name = "Renamed Co"
    profile.save()
    detail = api.get(f"/api/agreements/{signed['id']}/").json()
    assert detail["provider"]["business_name"] == "SchoolMS"
    assert api.get("/api/agreements/preview/?plan=pro&cycle=yearly").json()["provider"]["business_name"] == "Renamed Co"


def test_expired_institute_can_still_sign_and_cancel(api, admin_a, school_a):
    sub = school_a.subscription
    sub.current_period_end = timezone.now() - datetime.timedelta(days=2)
    sub.save()
    api.force_authenticate(admin_a)
    assert api.get("/api/students/").status_code == 402
    signed = api.post("/api/agreements/", SIGN, format="json")
    assert signed.status_code == 201
    cancelled = api.post(f"/api/agreements/{signed.json()['id']}/", {"action": "cancel"}, format="json").json()
    assert cancelled["status"] == "cancelled"
    assert api.post(f"/api/agreements/{signed.json()['id']}/", {"payment_reference": "x"}, format="json").status_code == 400


def test_owner_created_institute_accepts_trial_later(api, admin_a):
    api.force_authenticate(admin_a)
    assert api.get("/api/agreements/").json() == []
    assert api.post("/api/agreements/accept-trial/", {"accept": True, "signer_name": ""}, format="json").status_code == 400
    res = api.post("/api/agreements/accept-trial/", {"accept": True, "signer_name": "Admin A"}, format="json")
    assert res.status_code == 201 and res.json()["kind"] == "trial"
    assert api.post("/api/agreements/accept-trial/", {"accept": True, "signer_name": "Admin A"}, format="json").status_code == 400


def test_access_rules(api, admin_a, admin_b, make_user, school_a, super_admin):
    api.force_authenticate(admin_a)
    signed = api.post("/api/agreements/", SIGN, format="json").json()
    api.force_authenticate(admin_b)
    assert api.get(f"/api/agreements/{signed['id']}/").status_code == 404
    assert api.get("/api/agreements/").json() == []
    api.force_authenticate(make_user("t", Role.TEACHER, school_a))
    assert api.get("/api/agreements/").status_code == 403
    api.force_authenticate(admin_a)
    assert api.get("/api/platform/profile/").status_code == 403
    api.force_authenticate(super_admin)
    profile = api.patch("/api/platform/profile/", {"business_name": "EduSoft", "grace_days": 10}, format="json").json()
    assert profile["business_name"] == "EduSoft" and profile["grace_days"] == 10
    assert api.patch("/api/platform/profile/", {"data_retention_days": 5}, format="json").status_code == 400
    assert api.post(f"/api/platform/tenants/{school_a.pk}/record-payment/",
                    {"plan": "pro", "billing_cycle": "monthly", "amount": "1", "currency": "PKR", "method": "cash", "agreement": 999999},
                    format="json").status_code == 400

import hashlib
import hmac
from decimal import Decimal
from urllib.parse import parse_qs, urlparse

import pytest

from apps.academics.models import AcademicSession, Program, Section
from apps.accounts.models import Role
from apps.fees.models import Invoice, InvoiceItem
from apps.payments import gateways
from apps.payments.models import GatewayAccount, OnlinePayment
from apps.students.models import Enrollment, Guardian, Student, StudentGuardian

SALT = "s3cr3tSalt"
HASH_KEY = "0123456789abcdef"


def auth(api, user):
    api.force_authenticate(user)
    return api


@pytest.fixture
def school(school_a, make_user):
    session = AcademicSession.objects.create(tenant=school_a, name="S", start_date="2026-04-01", end_date="2027-03-31", is_current=True)
    program = Program.objects.create(tenant=school_a, name="Class 5")
    section = Section.objects.create(tenant=school_a, program=program, session=session, name="A")
    ali = Student.objects.create(tenant=school_a, admission_no="1", first_name="Ali", gender="male")
    sara = Student.objects.create(tenant=school_a, admission_no="2", first_name="Sara", gender="female")
    for s in (ali, sara):
        Enrollment.objects.create(tenant=school_a, student=s, section=section)
    invoices = {}
    for n, s in enumerate((ali, sara), start=1):
        inv = Invoice.objects.create(tenant=school_a, number=n, student=s, session=session, title="October fee",
                                     issue_date="2026-10-01", due_date="2026-10-10")
        InvoiceItem.objects.create(invoice=inv, description="Tuition", amount=Decimal("3000"))
        inv.refresh_totals()
        invoices[s.first_name] = inv
    parent = make_user("raza", Role.PARENT, school_a)
    guardian = Guardian.objects.create(tenant=school_a, name="Raza", user=parent)
    StudentGuardian.objects.create(student=ali, guardian=guardian)
    GatewayAccount.objects.create(tenant=school_a, provider="jazzcash", is_enabled=True, merchant_id="MC123",
                                  password="pw", secret=SALT)
    GatewayAccount.objects.create(tenant=school_a, provider="easypaisa", is_enabled=True, merchant_id="4321",
                                  secret=HASH_KEY)
    return {"ali": invoices["Ali"], "sara": invoices["Sara"], "parent": parent}


# --- Signing -----------------------------------------------------------------------

def test_jazzcash_hash_matches_spec():
    fields = {"pp_Amount": "300000", "pp_TxnRefNo": "T1", "pp_Version": "1.1", "pp_TxnType": "",
              "pp_MerchantID": "MC123", "ppmpf_1": "", "pp_SecureHash": "ignored"}
    # Spec: salt & non-empty pp_ values sorted by field name, joined with &, HMAC-SHA256 keyed with the salt.
    message = f"{SALT}&300000&MC123&T1&1.1"
    expected = hmac.new(SALT.encode(), message.encode(), hashlib.sha256).hexdigest().upper()
    assert gateways.jazzcash_hash(fields, SALT) == expected


def test_easypaisa_request_is_encrypted_correctly(school):
    account = GatewayAccount.objects.get(provider="easypaisa")
    import datetime

    req = gateways.easypaisa_request(account, "TREF1", Decimal("3000"), "https://x/pb?ref=TREF1", datetime.datetime(2026, 10, 27, 10, 0, 0))
    fields = req["fields"]
    assert req["action"].startswith("https://easypaystg.easypaisa.com.pk/")
    assert fields["amount"] == "3000.0"
    plain = gateways.easypaisa_decrypt(fields["merchantHashedReq"], HASH_KEY)
    assert plain == (
        "amount=3000.0&autoRedirect=1&expiryDate=20261028 100000&orderRefNum=TREF1"
        "&postBackURL=https://x/pb?ref=TREF1&storeId=4321"
    )


# --- Settings ----------------------------------------------------------------------

def test_settings_hide_secrets_and_keep_them_when_blank(api, admin_a, school):
    api = auth(api, admin_a)
    body = api.get("/api/pay/settings/").json()
    jc = next(a for a in body["accounts"] if a["provider"] == "jazzcash")
    assert jc["has_secret"] and jc["is_ready"]
    assert "secret" not in jc and "password" not in jc
    assert body["urls"]["jazzcash_return"].endswith("/api/pay/jazzcash/return/")
    res = api.patch("/api/pay/settings/", {"provider": "jazzcash", "merchant_id": "MC999", "secret": ""}, format="json")
    assert res.status_code == 200
    account = GatewayAccount.objects.get(provider="jazzcash")
    assert account.merchant_id == "MC999" and account.secret == SALT


def test_settings_validation(api, admin_a, school, school_a):
    api = auth(api, admin_a)
    res = api.patch("/api/pay/settings/", {"provider": "easypaisa", "secret": "short"}, format="json")
    assert res.status_code == 400
    GatewayAccount.objects.filter(provider="jazzcash").update(password="")
    res = api.patch("/api/pay/settings/", {"provider": "jazzcash", "is_enabled": True}, format="json")
    assert res.status_code == 400
    school_a.currency = "USD"
    school_a.save()
    res = api.patch("/api/pay/settings/", {"provider": "easypaisa", "is_enabled": True}, format="json")
    assert "PKR" in res.json()[0]


def test_only_admin_sees_settings(api, school):
    assert auth(api, school["parent"]).get("/api/pay/settings/").status_code == 403


def test_options(api, admin_a, school):
    assert [o["provider"] for o in auth(api, school["parent"]).get("/api/pay/options/").json()] == ["jazzcash", "easypaisa"]
    assert "demo" in [o["provider"] for o in auth(api, admin_a).get("/api/pay/options/").json()]


# --- JazzCash flow -------------------------------------------------------------------

def start(api, invoice, provider):
    return api.post("/api/pay/start/", {"invoice": invoice.pk, "provider": provider}, format="json")


def jazzcash_reply(start_body, code="000", amount=None):
    fields = start_body["fields"]
    reply = {
        "pp_Amount": amount or fields["pp_Amount"], "pp_BillReference": fields["pp_BillReference"],
        "pp_Language": "EN", "pp_MerchantID": fields["pp_MerchantID"], "pp_ResponseCode": code,
        "pp_ResponseMessage": "Thank you for Using JazzCash" if code == "000" else "Declined",
        "pp_RetreivalReferenceNo": "123456789012", "pp_TxnCurrency": "PKR", "pp_TxnDateTime": fields["pp_TxnDateTime"],
        "pp_TxnRefNo": fields["pp_TxnRefNo"], "pp_TxnType": "MWALLET", "pp_Version": "1.1",
    }
    reply["pp_SecureHash"] = gateways.jazzcash_hash(reply, SALT)
    return reply


def test_parent_pays_with_jazzcash(api, school, client):
    res = start(auth(api, school["parent"]), school["ali"], "jazzcash")
    assert res.status_code == 200, res.json()
    body = res.json()
    assert body["action"].startswith("https://sandbox.jazzcash.com.pk/")
    fields = body["fields"]
    assert fields["pp_Amount"] == "300000"  # paisa
    assert len(fields["pp_TxnRefNo"]) <= 20
    assert fields["pp_SecureHash"] == gateways.jazzcash_hash(fields, SALT)

    reply = client.post("/api/pay/jazzcash/return/", jazzcash_reply(body))
    assert reply.status_code == 302
    assert "/pay/result/?ref=" in reply["Location"]
    school["ali"].refresh_from_db()
    assert school["ali"].status == "paid"
    payment = school["ali"].payments.get()
    assert payment.method == "jazzcash" and payment.received_by is None
    # The gateway may post twice: no second payment.
    client.post("/api/pay/jazzcash/return/", jazzcash_reply(body))
    assert school["ali"].payments.count() == 1
    status = auth(api, school["parent"]).get(f"/api/pay/status/?ref={fields['pp_TxnRefNo']}").json()
    assert status["status"] == "success"


@pytest.mark.parametrize("tamper", ["hash", "amount", "declined"])
def test_jazzcash_bad_replies_do_not_pay(api, school, client, tamper):
    body = start(auth(api, school["parent"]), school["ali"], "jazzcash").json()
    reply = jazzcash_reply(body, code="124" if tamper == "declined" else "000")
    if tamper == "hash":
        reply["pp_ResponseCode"] = "000"
        reply["pp_SecureHash"] = "0" * 64
    if tamper == "amount":
        reply = jazzcash_reply(body, amount="100")
    client.post("/api/pay/jazzcash/return/", reply)
    school["ali"].refresh_from_db()
    assert school["ali"].status == "unpaid"
    assert OnlinePayment.objects.get().status == "failed"


def test_parent_cannot_pay_other_childs_bill(api, school):
    assert start(auth(api, school["parent"]), school["sara"], "jazzcash").status_code == 404


def test_parent_cannot_use_demo(api, school):
    assert start(auth(api, school["parent"]), school["ali"], "demo").status_code == 403


def test_cannot_pay_paid_bill_or_disabled_method(api, admin_a, school):
    GatewayAccount.objects.filter(provider="easypaisa").update(is_enabled=False)
    api = auth(api, admin_a)
    assert start(api, school["ali"], "easypaisa").status_code == 400
    school["ali"].status = "paid"
    school["ali"].save()
    assert start(api, school["ali"], "jazzcash").status_code == 400


# --- Easypaisa flow ------------------------------------------------------------------

def test_easypaisa_flow_with_ipn(api, school, client, monkeypatch):
    body = start(auth(api, school["parent"]), school["ali"], "easypaisa").json()
    ref = body["fields"]["orderRefNum"]
    postback = body["fields"]["postBackURL"]
    path = urlparse(postback).path
    # Step 1: token -> page that posts to Confirm.jsf with a clean postback URL.
    page = client.get(path, {"ref": ref, "auth_token": "TOKEN123"})
    html = page.content.decode()
    assert "Confirm.jsf" in html and "TOKEN123" in html
    assert "auth_token=TOKEN123" not in html  # the postBackURL does not carry the token
    # Step 2: final redirect says Success -> still waiting for IPN.
    final = client.get(path, {"ref": ref, "status": "Success", "orderRefNumber": ref})
    assert final.status_code == 302
    school["ali"].refresh_from_db()
    assert school["ali"].status == "unpaid"
    # IPN confirms.
    monkeypatch.setattr("apps.payments.views.fetch_ipn", lambda url: {
        "order_id": ref, "store_id": "4321", "transaction_status": "PAID", "transaction_amount": "3000.0",
        "transaction_id": "EP-99",
    })
    assert client.get("/api/pay/easypaisa/ipn/", {"url": "https://easypay.easypaisa.com.pk/ipn/1"}).status_code == 200
    school["ali"].refresh_from_db()
    assert school["ali"].status == "paid"
    assert school["ali"].payments.get().method == "easypaisa"


def test_easypaisa_ipn_wrong_amount_is_ignored(api, school, client, monkeypatch):
    ref = start(auth(api, school["parent"]), school["ali"], "easypaisa").json()["fields"]["orderRefNum"]
    monkeypatch.setattr("apps.payments.views.fetch_ipn", lambda url: {
        "order_id": ref, "store_id": "4321", "transaction_status": "PAID", "transaction_amount": "10.0",
    })
    client.get("/api/pay/easypaisa/ipn/", {"url": "https://easypay.easypaisa.com.pk/ipn/1"})
    school["ali"].refresh_from_db()
    assert school["ali"].status == "unpaid"


def test_ipn_only_fetches_easypaisa_urls():
    from apps.payments.views import fetch_ipn

    for url in ("http://easypay.easypaisa.com.pk/x", "https://evil.example.com/x", "https://easypaisa.com.pk.evil.com/x"):
        with pytest.raises(ValueError):
            fetch_ipn(url)


def test_easypaisa_failure_marks_failed(api, school, client):
    body = start(auth(api, school["parent"]), school["ali"], "easypaisa").json()
    ref = body["fields"]["orderRefNum"]
    client.get(urlparse(body["fields"]["postBackURL"]).path, {"ref": ref, "status": "Failure", "desc": "Cancelled by user"})
    assert OnlinePayment.objects.get().message == "Cancelled by user"


# --- Demo ------------------------------------------------------------------------------

def test_demo_payment_by_admin(api, admin_a, school):
    api = auth(api, admin_a)
    body = start(api, school["sara"], "demo").json()
    ref = parse_qs(urlparse(body["redirect"]).query)["ref"][0]
    res = api.post("/api/pay/demo/complete/", {"reference": ref, "outcome": "success"}, format="json")
    assert res.json()["status"] == "success"
    school["sara"].refresh_from_db()
    assert school["sara"].status == "paid"
    assert "Demo payment" in school["sara"].payments.get().reference
    assert api.post("/api/pay/demo/complete/", {"reference": ref, "outcome": "success"}, format="json").status_code == 400
    attempts = api.get(f"/api/pay/attempts/?invoice={school['sara'].pk}").json()
    assert attempts[0]["provider"] == "demo"


def test_plan_without_online_payments(api, admin_a, school, school_a):
    plan = school_a.subscription.plan
    plan.features = [f for f in plan.features if f != "online_payments"]
    plan.save()
    assert auth(api, admin_a).get("/api/pay/options/").status_code == 402

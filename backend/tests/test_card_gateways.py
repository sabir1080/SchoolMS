"""Stripe and Safepay: a payment counts only after the server verifies it (never the redirect alone)."""

import hashlib
import hmac
import io
import json
import time
from urllib.parse import parse_qs, urlparse

import pytest

from apps.payments import gateways
from apps.payments.models import GatewayAccount, OnlinePayment
from tests.test_payments import auth, school, start  # noqa: F401  (fixture)

STRIPE_KEY = "sk_test_51abc"
WHSEC = "whsec_test123"
SAFEPAY_SECRET = "sp-secret"


class FakeGateway:
    """Stands in for urllib.request.urlopen: records requests and replies with the given JSON."""

    def __init__(self, replies):
        self.replies, self.requests = replies, []

    def __call__(self, request, timeout):
        self.requests.append(request)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply

        class Resp(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        return Resp(json.dumps(reply).encode())


@pytest.fixture
def stripe(school, school_a):  # noqa: F811
    GatewayAccount.objects.create(tenant=school_a, provider="stripe", is_enabled=True, secret=STRIPE_KEY, password=WHSEC, test_mode=True)
    return school


def session(ref, amount=300000, status="paid", currency="pkr"):
    return {"id": "cs_test_1", "object": "checkout.session", "client_reference_id": ref, "amount_total": amount,
            "currency": currency, "payment_status": status, "payment_intent": "pi_123", "url": "https://checkout.stripe.com/c/pay/cs_test_1"}


def test_stripe_checkout_return_verifies_with_stripe(api, stripe, client, monkeypatch):
    fake = FakeGateway([session("x")])
    monkeypatch.setattr(__import__("urllib.request").request, "urlopen", fake)
    res = start(auth(api, stripe["parent"]), stripe["ali"], "stripe")
    assert res.status_code == 200, res.json()
    assert res.json()["redirect_url"] == "https://checkout.stripe.com/c/pay/cs_test_1"
    sent = fake.requests[0]
    form = parse_qs(sent.data.decode())
    ref = form["client_reference_id"][0]
    assert sent.full_url == "https://api.stripe.com/v1/checkout/sessions" and sent.get_header("Authorization").startswith("Basic ")
    assert form["line_items[0][price_data][unit_amount]"] == ["300000"] and form["line_items[0][price_data][currency]"] == ["pkr"]
    assert "/api/pay/stripe/return/?ref=" in form["success_url"][0] and "cancel=1" in form["cancel_url"][0]

    # A forged return without Stripe's confirmation does nothing.
    fake.replies = [session(ref, status="unpaid")]
    client.get(f"/api/pay/stripe/return/?ref={ref}")
    assert OnlinePayment.objects.get(reference=ref).status == "pending"
    # Wrong amount is refused too.
    fake.replies = [session(ref, amount=100)]
    client.get(f"/api/pay/stripe/return/?ref={ref}")
    assert OnlinePayment.objects.get(reference=ref).status == "pending"
    fake.replies = [session(ref)]
    res = client.get(f"/api/pay/stripe/return/?ref={ref}")
    assert res.status_code == 302 and "/pay/result/?ref=" in res["Location"]
    assert fake.requests[-1].full_url.endswith("/v1/checkout/sessions/cs_test_1")
    stripe["ali"].refresh_from_db()
    assert stripe["ali"].status == "paid" and stripe["ali"].payments.get().method == "card"


def signed(payload, secret=WHSEC, t=None):
    t = t or int(time.time())
    sig = hmac.new(secret.encode(), f"{t}.".encode() + payload, hashlib.sha256).hexdigest()
    return f"t={t},v1={sig}"


def test_stripe_webhook_needs_a_valid_signature(api, stripe, client, monkeypatch):
    fake = FakeGateway([session("x")])
    monkeypatch.setattr(__import__("urllib.request").request, "urlopen", fake)
    start(auth(api, stripe["parent"]), stripe["ali"], "stripe")
    ref = parse_qs(fake.requests[0].data.decode())["client_reference_id"][0]
    payload = json.dumps({"type": "checkout.session.completed", "data": {"object": session(ref)}}).encode()
    url = "/api/pay/stripe/webhook/alpha/"
    assert client.post(url, payload, content_type="application/json", HTTP_STRIPE_SIGNATURE=signed(payload, "whsec_wrong")).status_code == 400
    assert client.post(url, payload, content_type="application/json", HTTP_STRIPE_SIGNATURE=signed(payload, t=int(time.time()) - 3600)).status_code == 400
    assert client.post(url, payload, content_type="application/json").status_code == 400
    assert OnlinePayment.objects.get(reference=ref).status == "pending"
    assert client.post(url, payload, content_type="application/json", HTTP_STRIPE_SIGNATURE=signed(payload)).status_code == 200
    assert OnlinePayment.objects.get(reference=ref).status == "success"
    # Repeated delivery is harmless.
    client.post(url, payload, content_type="application/json", HTTP_STRIPE_SIGNATURE=signed(payload))
    assert stripe["ali"].payments.count() == 1


def test_stripe_cancel_and_unreachable(api, stripe, client, monkeypatch):
    fake = FakeGateway([OSError("blocked")])
    monkeypatch.setattr(__import__("urllib.request").request, "urlopen", fake)
    res = start(auth(api, stripe["parent"]), stripe["ali"], "stripe")
    assert res.status_code == 400 and "could not open the payment page" in str(res.json())
    assert OnlinePayment.objects.get().status == "failed"
    fake.replies = [session("x")]
    start(auth(api, stripe["parent"]), stripe["ali"], "stripe")
    ref = OnlinePayment.objects.filter(status="pending").get().reference
    fake.replies = [session(ref, status="unpaid")]
    client.get(f"/api/pay/stripe/return/?ref={ref}&cancel=1")
    assert OnlinePayment.objects.get(reference=ref).message == "Cancelled"


def test_stripe_settings(api, admin_a, school):  # noqa: F811
    api = auth(api, admin_a)
    assert api.patch("/api/pay/settings/", {"provider": "stripe", "secret": "pk_test_x"}, format="json").status_code == 400
    assert api.patch("/api/pay/settings/", {"provider": "stripe", "password": "nope"}, format="json").status_code == 400
    data = api.patch("/api/pay/settings/", {"provider": "stripe", "secret": "sk_live_abc", "password": WHSEC, "is_enabled": True}, format="json").json()
    account = next(a for a in data["accounts"] if a["provider"] == "stripe")
    assert account["is_ready"] and account["is_enabled"] and account["test_mode"] is False and account["currency_ok"]
    assert data["urls"]["stripe_webhook"].endswith("/api/pay/stripe/webhook/alpha/")
    assert "sk_live_abc" not in json.dumps(data) and WHSEC not in json.dumps(data)


def test_stripe_takes_other_currencies_but_safepay_needs_pkr(api, admin_a, school, school_a):  # noqa: F811
    school_a.currency = "USD"
    school_a.save()
    api = auth(api, admin_a)
    assert api.patch("/api/pay/settings/", {"provider": "stripe", "secret": STRIPE_KEY, "is_enabled": True}, format="json").status_code == 200
    res = api.patch("/api/pay/settings/", {"provider": "safepay", "merchant_id": "sec_abc", "secret": SAFEPAY_SECRET, "is_enabled": True}, format="json")
    assert res.status_code == 400 and "only accepts payments in PKR" in str(res.json())
    assert gateways.minor_units("12.5", "USD") == 1250 and gateways.minor_units("500", "JPY") == 500


@pytest.fixture
def safepay(school, school_a):  # noqa: F811
    GatewayAccount.objects.create(tenant=school_a, provider="safepay", is_enabled=True, merchant_id="sec_key", secret=SAFEPAY_SECRET, test_mode=True)
    return school


def test_safepay_return_needs_the_signature(api, safepay, client, monkeypatch):
    fake = FakeGateway([{"data": {"token": "track_abc"}}])
    monkeypatch.setattr(__import__("urllib.request").request, "urlopen", fake)
    res = start(auth(api, safepay["parent"]), safepay["ali"], "safepay")
    assert res.status_code == 200, res.json()
    url = urlparse(res.json()["redirect_url"])
    q = parse_qs(url.query)
    assert url.netloc == "sandbox.api.getsafepay.com" and url.path == "/components"
    assert q["beacon"] == ["track_abc"] and q["env"] == ["sandbox"]
    ref = q["order_id"][0]
    init = json.loads(fake.requests[0].data)
    assert fake.requests[0].full_url == "https://sandbox.api.getsafepay.com/order/v1/init"
    assert init == {"client": "sec_key", "amount": 3000.0, "currency": "PKR", "environment": "sandbox"}

    good = hmac.new(SAFEPAY_SECRET.encode(), b"track_abc", hashlib.sha256).hexdigest()
    client.get(f"/api/pay/safepay/return/?ref={ref}&tracker=track_abc&sig=bad")
    client.get(f"/api/pay/safepay/return/?ref={ref}&tracker=track_other&sig={hmac.new(SAFEPAY_SECRET.encode(), b'track_other', hashlib.sha256).hexdigest()}")
    op = OnlinePayment.objects.get(reference=ref)
    assert op.status == "pending" and op.message == "The payment could not be verified."
    res = client.get(f"/api/pay/safepay/return/?ref={ref}&tracker=track_abc&reference=SP-77&sig={good}")
    assert res.status_code == 302
    safepay["ali"].refresh_from_db()
    assert safepay["ali"].status == "paid" and "SP-77" in safepay["ali"].payments.get().reference


def test_parent_sees_new_options(api, stripe, school_a):
    GatewayAccount.objects.create(tenant=school_a, provider="safepay", is_enabled=True, merchant_id="k", secret="s")
    names = [o["provider"] for o in auth(api, stripe["parent"]).get("/api/pay/options/").json()]
    assert set(names) == {"jazzcash", "easypaisa", "stripe", "safepay"}

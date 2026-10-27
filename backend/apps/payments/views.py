import json
import logging
import urllib.request
from urllib.parse import urlencode, urlparse

from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape
from rest_framework import serializers
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Role
from apps.core.permissions import HasRole
from apps.fees.models import Invoice
from apps.fees.views import money
from apps.subscriptions.features import Feature
from apps.subscriptions.gating import ActiveSubscription, RequiresFeature

from . import gateways
from .models import PKR_ONLY, REAL_PROVIDERS, GatewayAccount, OnlinePayment, OnlinePaymentStatus, Provider
from .services import complete, fail, invoice_is_open, new_reference

logger = logging.getLogger(__name__)


def frontend_result(reference):
    return HttpResponseRedirect(f"{settings.FRONTEND_URL}/pay/result/?{urlencode({'ref': reference})}")


def payment_data(op):
    return {
        "reference": op.reference,
        "provider": op.provider,
        "provider_label": op.get_provider_display(),
        "amount": money(op.amount),
        "status": op.status,
        "message": op.message,
        "invoice": op.invoice_id,
        "invoice_title": op.invoice.title,
        "student": op.invoice.student.full_name,
        "test_mode": op.test_mode,
        "created_at": op.created_at,
    }


class TenantPaymentsView(APIView):
    """Logged-in institute users; plan must include online payments."""

    required_feature = Feature.ONLINE_PAYMENTS
    roles = (Role.ADMIN, Role.PARENT, Role.STUDENT)

    def get_permissions(self):
        return [HasRole.for_roles(*self.roles)(), ActiveSubscription(), RequiresFeature()]

    @property
    def tenant(self):
        return self.request.user.tenant


# --- Settings (admin) --------------------------------------------------------------

class AccountUpdateSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=[(p.value, p.label) for p in REAL_PROVIDERS])
    is_enabled = serializers.BooleanField(required=False)
    test_mode = serializers.BooleanField(required=False)
    merchant_id = serializers.CharField(max_length=50, required=False, allow_blank=True)
    # Blank means "keep the saved value"; secrets are never sent back.
    password = serializers.CharField(max_length=100, required=False, allow_blank=True, trim_whitespace=False)
    secret = serializers.CharField(max_length=100, required=False, allow_blank=True, trim_whitespace=False)

    def validate_secret(self, value):
        provider = self.initial_data.get("provider")
        if value and provider == Provider.EASYPAISA and len(value.encode()) != 16:
            raise serializers.ValidationError("The Easypaisa hash key must be exactly 16 characters.")
        if value and provider == Provider.STRIPE and not value.startswith(("sk_test_", "sk_live_", "rk_test_", "rk_live_")):
            raise serializers.ValidationError("Use the Stripe secret key that starts with sk_test_ or sk_live_.")
        return value

    def validate_password(self, value):
        if value and self.initial_data.get("provider") == Provider.STRIPE and not value.startswith("whsec_"):
            raise serializers.ValidationError("The Stripe webhook signing secret starts with whsec_.")
        return value


class PaymentSettingsView(TenantPaymentsView):
    roles = (Role.ADMIN,)

    def accounts(self):
        existing = {a.provider: a for a in GatewayAccount.objects.filter(tenant=self.tenant)}
        return [existing.get(p) or GatewayAccount(tenant=self.tenant, provider=p) for p in REAL_PROVIDERS]

    def data(self):
        build = self.request.build_absolute_uri
        return {
            "currency": self.tenant.currency,
            "currency_supported": self.tenant.currency == "PKR",
            "accounts": [
                {
                    "provider": a.provider,
                    "label": a.get_provider_display(),
                    "is_enabled": a.is_enabled,
                    "test_mode": a.test_mode,
                    "merchant_id": a.merchant_id,
                    "has_password": bool(a.password),
                    "has_secret": bool(a.secret),
                    "is_ready": a.is_ready,
                    "currency_ok": a.provider not in PKR_ONLY or self.tenant.currency == "PKR",
                }
                for a in self.accounts()
            ],
            # Give these to the gateways when registering the merchant account.
            "urls": {
                "jazzcash_return": build(reverse("pay-jazzcash-return")),
                "easypaisa_postback": build(reverse("pay-easypaisa-postback")),
                "easypaisa_ipn": build(reverse("pay-easypaisa-ipn")),
                "stripe_webhook": build(reverse("pay-stripe-webhook", args=[self.tenant.slug])),
            },
        }

    def get(self, request):
        return Response(self.data())

    def patch(self, request):
        serializer = AccountUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        account, _ = GatewayAccount.objects.get_or_create(tenant=self.tenant, provider=values.pop("provider"))
        for field in ("password", "secret"):
            if not values.get(field):
                values.pop(field, None)
        for field, value in values.items():
            setattr(account, field, value.strip() if field == "merchant_id" else value)
        if account.provider == Provider.STRIPE and account.secret:
            account.test_mode = "_test_" in account.secret  # Stripe keys say whether they are test keys
        if account.is_enabled:
            if not account.is_ready:
                raise ValidationError("Fill in all the account details before turning it on.")
            if account.provider in PKR_ONLY and self.tenant.currency != "PKR":
                raise ValidationError(f"{account.get_provider_display()} only accepts payments in PKR.")
        account.save()
        return Response(self.data())


# --- Paying ------------------------------------------------------------------------

def visible_invoice(user, invoice_id):
    """The invoice if this user may pay it: admins any in their institute, parents their
    children's, students their own."""
    invoice = Invoice.objects.filter(tenant=user.tenant, pk=invoice_id).select_related("student", "tenant").first()
    if invoice is None:
        raise NotFound("Invoice not found.")
    if user.role == Role.ADMIN:
        return invoice
    if user.role == Role.STUDENT and invoice.student.user_id == user.id:
        return invoice
    guardian = getattr(user, "guardian_profile", None)
    if user.role == Role.PARENT and guardian and guardian.students.filter(pk=invoice.student_id).exists():
        return invoice
    raise NotFound("Invoice not found.")


class PayOptionsView(TenantPaymentsView):
    """Which ways to pay online this user can use."""

    def get(self, request):
        options = [
            {"provider": a.provider, "label": a.get_provider_display(), "test_mode": a.test_mode}
            for a in GatewayAccount.objects.filter(tenant=self.tenant, is_enabled=True)
            if a.is_ready
        ]
        if request.user.role == Role.ADMIN:
            options.append({"provider": Provider.DEMO, "label": "Demo (testing only)", "test_mode": True})
        return Response(options)


class StartPaymentView(TenantPaymentsView):
    """Create a payment attempt and return the form the browser must post to the gateway."""

    def post(self, request):
        provider = request.data.get("provider")
        invoice = visible_invoice(request.user, request.data.get("invoice"))
        if not invoice_is_open(invoice):
            raise ValidationError("This bill has nothing left to pay.")
        if provider == Provider.DEMO:
            if request.user.role != Role.ADMIN:
                raise PermissionDenied("Demo payments are only for admins.")
            account = None
        else:
            account = GatewayAccount.objects.filter(tenant=self.tenant, provider=provider, is_enabled=True).first()
            if account is None or not account.is_ready:
                raise ValidationError("This payment method is not available.")
        op = OnlinePayment.objects.create(
            tenant=self.tenant,
            invoice=invoice,
            provider=provider,
            reference=new_reference(),
            amount=invoice.balance,
            started_by=request.user,
            test_mode=account.test_mode if account else True,
        )
        now = timezone.localtime()
        if provider == Provider.DEMO:
            redirect = {"redirect": f"/pay/demo/?{urlencode({'ref': op.reference})}"}
        elif provider == Provider.JAZZCASH:
            redirect = gateways.jazzcash_request(
                account, op.reference, op.amount, f"{invoice.title} - {invoice.student.full_name}",
                f"INV{invoice.number}", request.build_absolute_uri(reverse("pay-jazzcash-return")), now,
            )
        elif provider == Provider.EASYPAISA:
            postback = request.build_absolute_uri(reverse("pay-easypaisa-postback")) + "?" + urlencode({"ref": op.reference})
            redirect = gateways.easypaisa_request(account, op.reference, op.amount, postback, now)
        else:
            redirect = self.hosted_checkout(request, account, op, invoice)
        return Response({"payment": payment_data(op), **redirect})

    def hosted_checkout(self, request, account, op, invoice):
        """Stripe and Safepay: ask the gateway for a checkout page and send the browser there."""
        name = "pay-stripe-return" if op.provider == Provider.STRIPE else "pay-safepay-return"
        back = request.build_absolute_uri(reverse(name))
        return_url, cancel_url = f"{back}?{urlencode({'ref': op.reference})}", f"{back}?{urlencode({'ref': op.reference, 'cancel': 1})}"
        try:
            if op.provider == Provider.STRIPE:
                session = gateways.stripe_create_session(account, op.reference, op.amount, self.tenant.currency,
                                                         f"{invoice.title} - {invoice.student.full_name}", return_url, cancel_url)
                op.gateway_reference, url = session["id"], session["url"]
            else:
                op.gateway_reference = gateways.safepay_create_tracker(account, op.amount)
                url = gateways.safepay_checkout_url(account, op.gateway_reference, op.reference, return_url, cancel_url)
        except Exception as exc:  # network, bad keys or an unexpected reply
            logger.warning("%s checkout could not start: %s", op.provider, exc)
            fail(op, "Could not open the payment page.")
            raise ValidationError(f"{op.get_provider_display()} could not open the payment page. Please try again later.")
        op.save(update_fields=["gateway_reference", "updated_at"])
        return {"redirect_url": url}


class PaymentStatusView(TenantPaymentsView):
    def get(self, request):
        op = OnlinePayment.objects.filter(tenant=self.tenant, reference=request.query_params.get("ref", "")).first()
        if op is None:
            raise NotFound("Payment not found.")
        visible_invoice(request.user, op.invoice_id)
        return Response(payment_data(op))


class PaymentAttemptsView(TenantPaymentsView):
    """Online payment attempts for one invoice (admins)."""

    roles = (Role.ADMIN,)

    def get(self, request):
        attempts = OnlinePayment.objects.filter(tenant=self.tenant, invoice_id=request.query_params.get("invoice") or 0)
        return Response([payment_data(op) for op in attempts.select_related("invoice__student")])


class DemoCompleteView(TenantPaymentsView):
    """The demo gateway: an admin chooses whether the test payment succeeds."""

    roles = (Role.ADMIN,)

    def post(self, request):
        op = get_object_or_404(
            OnlinePayment, tenant=self.tenant, provider=Provider.DEMO, reference=request.data.get("reference", "")
        )
        if op.status != OnlinePaymentStatus.PENDING:
            raise ValidationError("This payment is already finished.")
        if request.data.get("outcome") == "success":
            if not invoice_is_open(op.invoice):
                fail(op, "The bill was already paid.")
            else:
                complete(op, "Demo payment completed")
        else:
            fail(op, "Cancelled")
        op.refresh_from_db()
        return Response(payment_data(op))


# --- Gateway callbacks (public: the customer's browser or the gateway calls these) ---

class GatewayCallbackView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def params(self, request):
        data = request.query_params.dict()
        if request.method == "POST":
            data.update({k: v for k, v in request.data.items()} if hasattr(request.data, "items") else {})
        return data


class JazzCashReturnView(GatewayCallbackView):
    def post(self, request):
        data = self.params(request)
        op = OnlinePayment.objects.filter(provider=Provider.JAZZCASH, reference=data.get("pp_TxnRefNo", "")).first()
        if op is None:
            return HttpResponse("Unknown transaction.", status=404)
        account = GatewayAccount.objects.filter(tenant=op.tenant, provider=Provider.JAZZCASH).first()
        ok, message = gateways.jazzcash_check(data, account, op.amount) if account else (False, "Not configured.")
        safe = {k: v for k, v in data.items() if k not in ("pp_Password",)}
        if ok:
            complete(op, message, data.get("pp_RetreivalReferenceNo") or data.get("pp_TxnRefNo", ""), safe)
        elif op.status != OnlinePaymentStatus.SUCCESS:
            logger.warning("JazzCash payment %s not accepted: %s", op.reference, message)
            fail(op, message, safe)
        return frontend_result(op.reference)

    get = post


class EasypaisaPostbackView(GatewayCallbackView):
    """Step 1: Easypaisa sends an auth_token, we confirm it. Step 2: the final status."""

    def get(self, request):
        data = self.params(request)
        op = OnlinePayment.objects.filter(provider=Provider.EASYPAISA, reference=data.get("ref", "")).first()
        if op is None:
            return HttpResponse("Unknown transaction.", status=404)
        account = GatewayAccount.objects.filter(tenant=op.tenant, provider=Provider.EASYPAISA).first()
        if data.get("auth_token") and account:
            # Same postback URL, but only with our ref: the final call must not carry the token again.
            postback = request.build_absolute_uri(reverse("pay-easypaisa-postback")) + "?" + urlencode({"ref": op.reference})
            form = gateways.easypaisa_confirm_form(account, data["auth_token"], postback)
            return auto_post_page(form)
        status = str(data.get("status", "")).lower()
        if op.status == OnlinePaymentStatus.PENDING:
            if status == "success":
                # Not trusted on its own (anyone can open this URL); the IPN confirms the payment.
                op.message = "Paid at Easypaisa, waiting for confirmation."
                op.save(update_fields=["message", "updated_at"])
            else:
                fail(op, str(data.get("desc") or "Payment was not completed."), data)
        return frontend_result(op.reference)

    post = get


IPN_HOST_SUFFIX = ".easypaisa.com.pk"


def fetch_ipn(url):
    parsed = urlparse(url)
    if parsed.scheme != "https" or not (parsed.hostname or "").endswith(IPN_HOST_SUFFIX):
        raise ValueError("IPN URL is not an Easypaisa address.")
    with urllib.request.urlopen(url, timeout=15) as response:  # noqa: S310 - https + host checked above
        return json.loads(response.read().decode())


class EasypaisaIPNView(GatewayCallbackView):
    """Easypaisa calls this with ?url=...; we fetch the transaction from that (Easypaisa) URL."""

    def get(self, request):
        url = self.params(request).get("url", "")
        try:
            ipn = fetch_ipn(url)
        except Exception as exc:  # bad URL, network or JSON
            logger.warning("Easypaisa IPN fetch failed: %s", exc)
            return HttpResponse("IPN could not be read.", status=400)
        op = OnlinePayment.objects.filter(provider=Provider.EASYPAISA, reference=str(ipn.get("order_id", ""))).first()
        if op is None:
            return HttpResponse("Unknown order.", status=404)
        account = GatewayAccount.objects.filter(tenant=op.tenant, provider=Provider.EASYPAISA).first()
        ok, message = gateways.easypaisa_ipn_check(ipn, account, op.reference, op.amount)
        if ok:
            complete(op, message, str(ipn.get("transaction_id", "")), ipn)
        elif str(ipn.get("transaction_status", "")).upper() in ("FAILED", "EXPIRED", "REVERSED"):
            fail(op, message, ipn)
        return HttpResponse("OK")

    post = get


class StripeReturnView(GatewayCallbackView):
    """The browser comes back from Stripe Checkout. We read the session from Stripe before marking it paid."""

    def get(self, request):
        data = self.params(request)
        op = OnlinePayment.objects.filter(provider=Provider.STRIPE, reference=data.get("ref", "")).select_related("tenant").first()
        if op is None:
            return HttpResponse("Unknown transaction.", status=404)
        account = GatewayAccount.objects.filter(tenant=op.tenant, provider=Provider.STRIPE).first()
        if op.status == OnlinePaymentStatus.PENDING and account and op.gateway_reference:
            try:
                session = gateways.stripe_call(account.secret, f"/v1/checkout/sessions/{op.gateway_reference}")
            except Exception as exc:
                logger.warning("Stripe session check failed: %s", exc)
                session = None
            if session is not None:
                ok, message = gateways.stripe_session_check(session, op.reference, op.amount, op.tenant.currency)
                if ok:
                    complete(op, message, str(session.get("payment_intent") or session.get("id")), session)
                elif data.get("cancel"):
                    fail(op, "Cancelled", session)
            elif data.get("cancel"):
                fail(op, "Cancelled")
        return frontend_result(op.reference)


class StripeWebhookView(GatewayCallbackView):
    """Stripe tells us about finished checkouts (also when the parent closed the browser before returning)."""

    def post(self, request, code):
        account = GatewayAccount.objects.filter(tenant__slug=code, provider=Provider.STRIPE).first()
        payload = request.body
        if account is None or not account.password or not gateways.stripe_verify_signature(
            payload, request.headers.get("Stripe-Signature", ""), account.password
        ):
            return HttpResponse("Bad signature.", status=400)
        event = json.loads(payload.decode() or "{}")
        session = (event.get("data") or {}).get("object") or {}
        op = OnlinePayment.objects.filter(tenant=account.tenant, provider=Provider.STRIPE,
                                          reference=str(session.get("client_reference_id", ""))).first()
        if op is None:
            return HttpResponse("OK")  # not one of ours (e.g. another product on the same Stripe account)
        if event.get("type") in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
            ok, message = gateways.stripe_session_check(session, op.reference, op.amount, account.tenant.currency)
            if ok:
                complete(op, message, str(session.get("payment_intent") or session.get("id")), session)
        elif event.get("type") in ("checkout.session.expired", "checkout.session.async_payment_failed"):
            fail(op, "Payment was not completed.", session)
        return HttpResponse("OK")


class SafepayReturnView(GatewayCallbackView):
    """The browser comes back from Safepay with the tracker and a signature made with the institute's secret key."""

    def get(self, request):
        data = self.params(request)
        op = OnlinePayment.objects.filter(provider=Provider.SAFEPAY, reference=data.get("ref", "")).first()
        if op is None:
            return HttpResponse("Unknown transaction.", status=404)
        account = GatewayAccount.objects.filter(tenant=op.tenant, provider=Provider.SAFEPAY).first()
        if op.status == OnlinePaymentStatus.PENDING:
            tracker = str(data.get("tracker", ""))
            if data.get("cancel"):
                fail(op, "Cancelled", data)
            elif account and tracker and tracker == op.gateway_reference and gateways.safepay_signature_ok(account, tracker, str(data.get("sig", ""))):
                complete(op, "Paid with Safepay", str(data.get("reference") or tracker), data)
            else:
                op.message = "The payment could not be verified."
                op.save(update_fields=["message", "updated_at"])
        return frontend_result(op.reference)

    post = get


def auto_post_page(form):
    """A tiny HTML page that posts ``form`` to the gateway straight away."""
    inputs = "".join(
        f'<input type="hidden" name="{escape(k)}" value="{escape(v)}">' for k, v in form["fields"].items()
    )
    html = (
        "<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width'>"
        "<title>Redirecting…</title></head><body onload='document.forms[0].submit()'>"
        f"<form method='post' action='{escape(form['action'])}'>{inputs}"
        "<p>Redirecting to the payment page…</p><button type='submit'>Continue</button></form></body></html>"
    )
    return HttpResponse(html)



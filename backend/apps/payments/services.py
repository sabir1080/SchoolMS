import logging
import secrets
import string

from django.db import transaction
from django.utils import timezone

from apps.core.timeutils import tenant_today
from apps.fees.models import InvoiceStatus
from apps.fees.services import record_payment
from apps.messaging.alerts import payment_alert

from .models import OnlinePayment, OnlinePaymentStatus, Provider

logger = logging.getLogger(__name__)

METHOD_FOR_PROVIDER = {Provider.JAZZCASH: "jazzcash", Provider.EASYPAISA: "easypaisa", Provider.DEMO: "other"}


def new_reference():
    """20 characters, letters and digits only (JazzCash allows at most 20)."""
    alphabet = string.ascii_uppercase + string.digits
    return "T" + timezone.now().strftime("%y%m%d%H%M%S") + "".join(secrets.choice(alphabet) for _ in range(7))


def invoice_is_open(invoice):
    return invoice.status in (InvoiceStatus.UNPAID, InvoiceStatus.PARTIAL) and invoice.balance > 0


@transaction.atomic
def complete(online_payment, message="Paid", gateway_reference="", response=None):
    """Mark a gateway payment as paid and record it on the invoice (safe to call twice)."""
    op = OnlinePayment.objects.select_for_update().get(pk=online_payment.pk)
    if op.status == OnlinePaymentStatus.SUCCESS:
        return op
    label = "Demo payment" if op.provider == Provider.DEMO else op.get_provider_display()
    op.payment = record_payment(
        op.invoice,
        amount=op.amount,
        date=tenant_today(op.tenant),
        method=METHOD_FOR_PROVIDER[op.provider],
        reference=f"{label} {gateway_reference or op.reference}"[:100],
    )
    op.status = OnlinePaymentStatus.SUCCESS
    op.message = message[:255]
    op.gateway_reference = gateway_reference[:100]
    if response is not None:
        op.response = response
    op.save()
    transaction.on_commit(lambda: notify_parent(op.payment))
    return op


def notify_parent(payment):
    """The payment is saved already; a messaging problem must not fail the gateway's callback."""
    try:
        payment_alert(payment)
    except Exception:  # noqa: BLE001
        logger.exception("Payment alert failed for payment %s", payment.pk)


def fail(online_payment, message, response=None):
    """Record a failed or cancelled attempt (a later confirmation can still mark it paid)."""
    if online_payment.status == OnlinePaymentStatus.SUCCESS:
        return online_payment
    online_payment.status = OnlinePaymentStatus.FAILED
    online_payment.message = message[:255]
    if response is not None:
        online_payment.response = response
    online_payment.save(update_fields=["status", "message", "response", "updated_at"])
    return online_payment

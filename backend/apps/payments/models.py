from django.conf import settings
from django.db import models

from apps.core.models import TenantScopedModel


class Provider(models.TextChoices):
    JAZZCASH = "jazzcash", "JazzCash"
    EASYPAISA = "easypaisa", "Easypaisa"
    SAFEPAY = "safepay", "Safepay"
    STRIPE = "stripe", "Card (Stripe)"
    DEMO = "demo", "Demo (testing only)"


REAL_PROVIDERS = (Provider.JAZZCASH, Provider.EASYPAISA, Provider.SAFEPAY, Provider.STRIPE)
# Gateways that only take Pakistani rupees; Stripe takes the institute's own currency.
PKR_ONLY = (Provider.JAZZCASH, Provider.EASYPAISA, Provider.SAFEPAY)


class GatewayAccount(TenantScopedModel):
    """An institute's merchant account with a payment gateway.

    JazzCash: merchant_id = Merchant ID, password = Password, secret = Integrity Salt.
    Easypaisa: merchant_id = Store ID, secret = Hash Key (password unused).
    Safepay: merchant_id = API key, secret = Secret key (signs the return), password unused.
    Stripe: secret = Secret key (sk_...), password = Webhook signing secret (whsec_..., optional), merchant_id unused.
    Secrets are never sent back by the API.
    """

    provider = models.CharField(max_length=20, choices=[(p.value, p.label) for p in REAL_PROVIDERS])
    is_enabled = models.BooleanField(default=False)
    test_mode = models.BooleanField(default=True, help_text="Use the gateway's sandbox / staging system")
    merchant_id = models.CharField(max_length=50, blank=True)
    password = models.CharField(max_length=100, blank=True)
    secret = models.CharField(max_length=100, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["tenant", "provider"], name="one_account_per_provider")]

    @property
    def is_ready(self):
        if self.provider == Provider.JAZZCASH:
            return bool(self.merchant_id and self.password and self.secret)
        if self.provider == Provider.STRIPE:
            return bool(self.secret)
        return bool(self.merchant_id and self.secret)


class OnlinePaymentStatus(models.TextChoices):
    PENDING = "pending", "Waiting for the gateway"
    SUCCESS = "success", "Paid"
    FAILED = "failed", "Failed or cancelled"


class OnlinePayment(TenantScopedModel):
    """One attempt to pay an invoice through a gateway."""

    invoice = models.ForeignKey("fees.Invoice", on_delete=models.CASCADE, related_name="online_payments")
    provider = models.CharField(max_length=20, choices=Provider.choices)
    reference = models.CharField(max_length=20, unique=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=10, choices=OnlinePaymentStatus.choices, default=OnlinePaymentStatus.PENDING)
    message = models.CharField(max_length=255, blank=True)
    gateway_reference = models.CharField(max_length=100, blank=True)
    response = models.JSONField(default=dict, blank=True)
    test_mode = models.BooleanField(default=False)
    started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    payment = models.OneToOneField(
        "fees.Payment", on_delete=models.SET_NULL, null=True, blank=True, related_name="online_payment"
    )

    class Meta:
        ordering = ["-created_at"]

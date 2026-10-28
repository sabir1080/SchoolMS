from django.conf import settings
from django.db import models

from apps.core.models import TenantScopedModel, TimeStampedModel


class ProviderProfile(TimeStampedModel):
    """The platform owner's business details and terms used in every agreement (one row)."""

    business_name = models.CharField(max_length=150, default="SchoolMS")
    owner_name = models.CharField(max_length=150, blank=True)
    address = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    payment_instructions = models.TextField(
        blank=True, help_text="Shown to institutes after they sign: bank account, JazzCash/Easypaisa numbers"
    )
    grace_days = models.PositiveSmallIntegerField(default=7)
    data_retention_days = models.PositiveSmallIntegerField(default=90)
    refund_policy = models.CharField(
        max_length=255, default="Fees paid for a subscription period are not refundable once that period has started."
    )

    @classmethod
    def get(cls):
        profile = cls.objects.first()
        return profile or cls.objects.create()


class Kind(models.TextChoices):
    TRIAL = "trial", "Free trial agreement"
    SUBSCRIPTION = "subscription", "Subscription agreement"


class Status(models.TextChoices):
    ACCEPTED = "accepted", "Accepted"  # free trial
    PENDING = "pending_payment", "Signed, payment pending"
    ACTIVE = "active", "Active"
    SUPERSEDED = "superseded", "Replaced by a newer agreement"
    CANCELLED = "cancelled", "Cancelled"


class SignedAgreement(TenantScopedModel):
    """One agreement an institute accepted, with the exact text it saw (later changes never alter it)."""

    kind = models.CharField(max_length=20, choices=Kind.choices)
    version = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=Status.choices)
    plan = models.ForeignKey("subscriptions.Plan", on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    billing_cycle = models.CharField(max_length=10, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, blank=True)
    # Who signed for the institute.
    institute_legal_name = models.CharField(max_length=200)
    institute_address = models.CharField(max_length=255, blank=True)
    signer_name = models.CharField(max_length=150)
    signer_designation = models.CharField(max_length=100, blank=True)
    signer_cnic = models.CharField(max_length=30, blank=True)
    signer_phone = models.CharField(max_length=30, blank=True)
    signature = models.CharField(max_length=150, help_text="Full name typed as the electronic signature")
    signed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    signed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.CharField(max_length=60, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    # Snapshot of what was agreed.
    provider = models.JSONField(default=dict)
    schedule = models.JSONField(default=dict)
    sections = models.JSONField(default=list)
    # Filled when the platform owner records the payment.
    payment_reference = models.CharField(max_length=100, blank=True, help_text="Reference the institute gave for its payment")
    payment = models.OneToOneField("subscriptions.SubscriptionPayment", on_delete=models.SET_NULL, null=True, blank=True, related_name="agreement")
    period_start = models.DateTimeField(null=True, blank=True)
    period_end = models.DateTimeField(null=True, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-signed_at", "-id"]

    @property
    def number(self):
        return f"AGR-{self.pk:05d}"

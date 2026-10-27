import math
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel

from .features import Feature


class BillingCycle(models.TextChoices):
    MONTHLY = "monthly", "Monthly"
    YEARLY = "yearly", "Yearly"


class Plan(TimeStampedModel):
    """A subscription plan. Limits set to ``None`` mean unlimited."""

    code = models.SlugField(max_length=30, unique=True)
    name = models.CharField(max_length=60)
    description = models.CharField(max_length=255, blank=True)
    max_students = models.PositiveIntegerField(null=True, blank=True)
    max_staff = models.PositiveIntegerField(null=True, blank=True)
    features = models.JSONField(default=list, help_text=f"Any of: {', '.join(Feature.values)}")
    is_public = models.BooleanField(default=True, help_text="Shown on pricing and billing pages")
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.name

    def has_feature(self, feature):
        return feature in self.features


class PlanPrice(models.Model):
    """Price of a plan in one currency for one billing cycle."""

    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="prices")
    currency = models.CharField(max_length=3)
    billing_cycle = models.CharField(max_length=10, choices=BillingCycle.choices)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["currency", "billing_cycle"]
        constraints = [
            models.UniqueConstraint(fields=["plan", "currency", "billing_cycle"], name="unique_plan_price"),
        ]

    def __str__(self):
        return f"{self.plan} {self.amount} {self.currency}/{self.billing_cycle}"


class SubscriptionStatus(models.TextChoices):
    TRIALING = "trialing", "Trial"
    ACTIVE = "active", "Active"
    PAST_DUE = "past_due", "Payment overdue"
    EXPIRED = "expired", "Expired"
    CANCELLED = "cancelled", "Cancelled"


USABLE_STATUSES = (SubscriptionStatus.TRIALING, SubscriptionStatus.ACTIVE)


class Subscription(TimeStampedModel):
    """The plan an institute is on, and until when it is paid for."""

    tenant = models.OneToOneField("tenants.Tenant", on_delete=models.CASCADE, related_name="subscription")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscriptions")
    status = models.CharField(max_length=20, choices=SubscriptionStatus.choices)
    billing_cycle = models.CharField(max_length=10, choices=BillingCycle.choices, default=BillingCycle.MONTHLY)
    current_period_start = models.DateTimeField(default=timezone.now)
    current_period_end = models.DateTimeField()

    def __str__(self):
        return f"{self.tenant} — {self.plan} ({self.status})"

    @property
    def effective_status(self):
        """The stored status, except a trial or paid period that has run out counts as expired."""
        if self.status in USABLE_STATUSES and timezone.now() > self.current_period_end:
            return SubscriptionStatus.EXPIRED
        return self.status

    @property
    def is_usable(self):
        return self.effective_status in USABLE_STATUSES

    @property
    def days_left(self):
        # Count a started day as a full day, so a fresh 14-day trial shows 14, not 13.
        seconds = (self.current_period_end - timezone.now()).total_seconds()
        return max(math.ceil(seconds / 86400), 0)

    def extend(self, cycle):
        """Move the period end forward by one cycle, starting from today if already expired."""
        start = max(self.current_period_end, timezone.now())
        if start != self.current_period_end:
            self.current_period_start = start
        self.current_period_end = start + (timedelta(days=365) if cycle == BillingCycle.YEARLY else timedelta(days=30))
        self.billing_cycle = cycle
        self.status = SubscriptionStatus.ACTIVE


class PaymentMethod(models.TextChoices):
    CASH = "cash", "Cash"
    BANK_TRANSFER = "bank_transfer", "Bank transfer"
    JAZZCASH = "jazzcash", "JazzCash"
    EASYPAISA = "easypaisa", "Easypaisa"
    CARD = "card", "Card"
    OTHER = "other", "Other"


class SubscriptionPayment(TimeStampedModel):
    """A payment an institute made to the platform for its subscription."""

    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name="payments")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="+")
    billing_cycle = models.CharField(max_length=10, choices=BillingCycle.choices)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3)
    method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        ordering = ["-created_at"]

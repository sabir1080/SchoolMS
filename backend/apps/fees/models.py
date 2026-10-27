from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Sum

from apps.core.models import TenantScopedModel


class Frequency(models.TextChoices):
    MONTHLY = "monthly", "Every month"
    ONE_TIME = "one_time", "Once per session"


class FeeHead(TenantScopedModel):
    """A kind of fee, e.g. Tuition Fee (monthly) or Admission Fee (once)."""

    name = models.CharField(max_length=100)
    frequency = models.CharField(max_length=10, choices=Frequency.choices, default=Frequency.MONTHLY)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]
        constraints = [models.UniqueConstraint(fields=["tenant", "name"], name="unique_fee_head_name")]

    def __str__(self):
        return self.name


class FeeRate(TenantScopedModel):
    """How much a fee head costs for one program in one session."""

    program = models.ForeignKey("academics.Program", on_delete=models.CASCADE, related_name="fee_rates")
    session = models.ForeignKey("academics.AcademicSession", on_delete=models.CASCADE, related_name="fee_rates")
    fee_head = models.ForeignKey(FeeHead, on_delete=models.CASCADE, related_name="rates")
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["program", "session", "fee_head"], name="unique_fee_rate"),
        ]


class DiscountType(models.TextChoices):
    AMOUNT = "amount", "Fixed amount"
    PERCENT = "percent", "Percent"


class StudentDiscount(TenantScopedModel):
    """A concession for one student on one fee head (e.g. sibling or scholarship discount)."""

    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="fee_discounts")
    fee_head = models.ForeignKey(FeeHead, on_delete=models.CASCADE, related_name="discounts")
    discount_type = models.CharField(max_length=10, choices=DiscountType.choices, default=DiscountType.AMOUNT)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=150, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["student", "fee_head"], name="one_discount_per_head")]

    def apply(self, amount):
        """The discount on ``amount`` (never more than the amount itself)."""
        if self.discount_type == DiscountType.PERCENT:
            off = (amount * self.value / Decimal(100)).quantize(Decimal("0.01"))
        else:
            off = self.value
        return min(off, amount)


class InvoiceStatus(models.TextChoices):
    UNPAID = "unpaid", "Unpaid"
    PARTIAL = "partial", "Partly paid"
    PAID = "paid", "Paid"
    CANCELLED = "cancelled", "Cancelled"


class Invoice(TenantScopedModel):
    """A fee bill (challan) for one student."""

    number = models.PositiveIntegerField()
    student = models.ForeignKey("students.Student", on_delete=models.PROTECT, related_name="invoices")
    session = models.ForeignKey("academics.AcademicSession", on_delete=models.PROTECT, related_name="invoices")
    # "YYYY-MM" for monthly bills made by "Generate"; blank for one-off bills.
    period = models.CharField(max_length=7, blank=True)
    title = models.CharField(max_length=100)
    issue_date = models.DateField()
    due_date = models.DateField()
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=InvoiceStatus.choices, default=InvoiceStatus.UNPAID)
    notes = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        ordering = ["-issue_date", "-number"]
        constraints = [
            models.UniqueConstraint(fields=["tenant", "number"], name="unique_invoice_number"),
            models.UniqueConstraint(
                fields=["student", "period"],
                condition=~models.Q(period="") & ~models.Q(status="cancelled"),
                name="one_invoice_per_student_period",
            ),
        ]

    @property
    def balance(self):
        return self.total - self.paid

    def refresh_totals(self):
        """Recalculate total, paid and status from items and payments, then save."""
        self.total = self.items.aggregate(s=Sum("amount"))["s"] or Decimal(0)
        self.total -= self.items.aggregate(s=Sum("discount"))["s"] or Decimal(0)
        self.paid = self.payments.aggregate(s=Sum("amount"))["s"] or Decimal(0)
        if self.status != InvoiceStatus.CANCELLED:
            if self.paid <= 0:
                self.status = InvoiceStatus.UNPAID
            elif self.paid < self.total:
                self.status = InvoiceStatus.PARTIAL
            else:
                self.status = InvoiceStatus.PAID
        self.save(update_fields=["total", "paid", "status", "updated_at"])


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="items")
    fee_head = models.ForeignKey(FeeHead, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    description = models.CharField(max_length=150)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        ordering = ["id"]

    @property
    def net(self):
        return self.amount - self.discount


class PaymentMethod(models.TextChoices):
    CASH = "cash", "Cash"
    BANK = "bank", "Bank deposit / transfer"
    JAZZCASH = "jazzcash", "JazzCash"
    EASYPAISA = "easypaisa", "Easypaisa"
    CARD = "card", "Card"
    OTHER = "other", "Other"


class Payment(TenantScopedModel):
    """Money received against an invoice."""

    receipt_number = models.PositiveIntegerField()
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()
    method = models.CharField(max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.CASH)
    reference = models.CharField(max_length=100, blank=True)
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        ordering = ["date", "id"]
        constraints = [models.UniqueConstraint(fields=["tenant", "receipt_number"], name="unique_receipt_number")]

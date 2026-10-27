from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.core.models import TenantScopedModel
from apps.fees.models import PaymentMethod


class Employee(TenantScopedModel):
    """A member of staff on the payroll: teachers (optionally linked to their login) and other staff."""

    name = models.CharField(max_length=150)
    designation = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    cnic = models.CharField("CNIC / ID number", max_length=30, blank=True)
    join_date = models.DateField(null=True, blank=True)
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2)
    allowance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal(0))
    bank_account = models.CharField(max_length=60, blank=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="employee_profile"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class PayslipStatus(models.TextChoices):
    UNPAID = "unpaid", "Unpaid"
    PAID = "paid", "Paid"


class Payslip(TenantScopedModel):
    """One month's salary for one employee. Salary figures are copied when the slip is made."""

    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="payslips")
    period = models.CharField(max_length=7)  # YYYY-MM
    basic = models.DecimalField(max_digits=12, decimal_places=2)
    allowance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal(0))
    bonus = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal(0))
    deduction = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal(0))
    note = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=10, choices=PayslipStatus.choices, default=PayslipStatus.UNPAID)
    paid_on = models.DateField(null=True, blank=True)
    method = models.CharField(max_length=20, choices=PaymentMethod.choices, blank=True)
    reference = models.CharField(max_length=100, blank=True)
    paid_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    class Meta:
        ordering = ["-period", "employee__name"]
        constraints = [models.UniqueConstraint(fields=["employee", "period"], name="one_payslip_per_month")]

    @property
    def gross(self):
        return self.basic + self.allowance + self.bonus

    @property
    def net(self):
        return self.gross - self.deduction

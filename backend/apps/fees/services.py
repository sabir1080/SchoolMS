from decimal import Decimal

from django.db import transaction
from django.db.models import Max

from apps.students.models import Enrollment, StudentStatus
from apps.students.services import lock_tenant

from .models import FeeRate, Frequency, Invoice, InvoiceItem, InvoiceStatus, Payment, StudentDiscount


def next_number(model, field, tenant):
    return (model.objects.filter(tenant=tenant).aggregate(m=Max(field))["m"] or 0) + 1


def month_title(period):
    """'2026-10' -> 'October 2026 fee'."""
    import calendar

    year, month = period.split("-")
    return f"{calendar.month_name[int(month)]} {year} fee"


def billable_items(student, program, session):
    """Fee items for one month: monthly heads, plus one-time heads not billed yet this session."""
    rates = FeeRate.objects.filter(program=program, session=session, fee_head__is_active=True, amount__gt=0).select_related("fee_head")
    already_billed = set(
        InvoiceItem.objects.filter(
            invoice__student=student, invoice__session=session, fee_head__frequency=Frequency.ONE_TIME
        )
        .exclude(invoice__status=InvoiceStatus.CANCELLED)
        .values_list("fee_head_id", flat=True)
    )
    discounts = {d.fee_head_id: d for d in StudentDiscount.objects.filter(student=student)}
    items = []
    for rate in sorted(rates, key=lambda r: (r.fee_head.sort_order, r.fee_head.name)):
        head = rate.fee_head
        if head.frequency == Frequency.ONE_TIME and head.id in already_billed:
            continue
        discount = discounts[head.id].apply(rate.amount) if head.id in discounts else Decimal(0)
        items.append({"fee_head": head, "description": head.name, "amount": rate.amount, "discount": discount})
    return items


@transaction.atomic
def generate_monthly_invoices(tenant, session, period, issue_date, due_date, sections=None, user=None):
    """Create one invoice per active student for ``period`` ('YYYY-MM').

    Students who already have a (non-cancelled) invoice for the period are skipped, so running it
    twice is safe. Returns counts.
    """
    tenant = lock_tenant(tenant)
    enrollments = Enrollment.objects.filter(
        tenant=tenant, session=session, student__status=StudentStatus.ACTIVE
    ).select_related("student", "section__program")
    if sections is not None:
        enrollments = enrollments.filter(section__in=sections)
    existing = set(
        Invoice.objects.filter(tenant=tenant, period=period).exclude(status=InvoiceStatus.CANCELLED).values_list("student_id", flat=True)
    )
    number = next_number(Invoice, "number", tenant)
    result = {"created": 0, "already_billed": 0, "nothing_to_bill": 0, "total_amount": Decimal(0)}
    for enrollment in enrollments:
        student = enrollment.student
        if student.id in existing:
            result["already_billed"] += 1
            continue
        items = billable_items(student, enrollment.section.program, session)
        if sum(i["amount"] - i["discount"] for i in items) <= 0:
            result["nothing_to_bill"] += 1
            continue
        invoice = Invoice.objects.create(
            tenant=tenant, number=number, student=student, session=session, period=period,
            title=month_title(period), issue_date=issue_date, due_date=due_date, created_by=user,
        )
        number += 1
        InvoiceItem.objects.bulk_create([InvoiceItem(invoice=invoice, **i) for i in items])
        invoice.refresh_totals()
        result["created"] += 1
        result["total_amount"] += invoice.total
    return result


@transaction.atomic
def create_invoice(tenant, student, session, title, issue_date, due_date, items, notes="", user=None):
    """A one-off invoice with the given items (dicts with description, amount, discount, fee_head)."""
    tenant = lock_tenant(tenant)
    invoice = Invoice.objects.create(
        tenant=tenant, number=next_number(Invoice, "number", tenant), student=student, session=session,
        title=title, issue_date=issue_date, due_date=due_date, notes=notes, created_by=user,
    )
    InvoiceItem.objects.bulk_create([InvoiceItem(invoice=invoice, **i) for i in items])
    invoice.refresh_totals()
    return invoice


@transaction.atomic
def record_payment(invoice, amount, date, method, reference="", user=None):
    tenant = lock_tenant(invoice.tenant)
    invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)
    payment = Payment.objects.create(
        tenant=tenant, receipt_number=next_number(Payment, "receipt_number", tenant), invoice=invoice,
        amount=amount, date=date, method=method, reference=reference, received_by=user,
    )
    invoice.refresh_totals()
    return payment

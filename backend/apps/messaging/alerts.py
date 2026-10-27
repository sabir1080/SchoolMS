"""The texts parents receive. Each builder queues messages through ``services.queue_and_send``."""

from decimal import Decimal

from apps.academics.models import Section
from apps.core.timeutils import tenant_today
from apps.fees.models import Invoice, InvoiceStatus
from apps.students.models import Enrollment, StudentStatus

from .models import Kind, Message, Status
from .services import alerts_enabled, queue_and_send, settings_for


def class_name(section):
    return f"{section.program.name} - {section.name}"


def absent_alerts(tenant, section, date, records, user=None):
    """Tell parents their child was absent today. Taking the attendance again does not repeat the alert, and
    an alert still waiting in the outbox is withdrawn when the child is marked present instead."""
    if date != tenant_today(tenant) or not alerts_enabled(tenant) or not settings_for(tenant).absent_alerts:
        return []
    present = [r["student"] for r in records if r["status"] != "absent"]
    Message.objects.filter(
        tenant=tenant, status=Status.PENDING, dedupe_key__in=[f"absent:{sid}:{date}" for sid in present]
    ).delete()
    absent = {r["student"] for r in records if r["status"] == "absent"}
    enrollments = Enrollment.objects.filter(section=section, student_id__in=absent).select_related("student")
    items = [
        (
            e.student,
            f"{tenant.name}: {e.student.full_name} ({class_name(section)}) was absent today, {date:%d %b %Y}. "
            "If this is a mistake, please contact the school.",
            f"absent:{e.student_id}:{date}",
        )
        for e in enrollments
    ]
    return queue_and_send(tenant, items, Kind.ABSENT, user)


def fee_reminders(tenant, user=None):
    """One reminder per student with overdue bills (at most once a day)."""
    today = tenant_today(tenant)
    overdue = (
        Invoice.objects.filter(tenant=tenant, status__in=[InvoiceStatus.UNPAID, InvoiceStatus.PARTIAL], due_date__lt=today)
        .select_related("student").order_by("due_date")
    )
    per_student = {}
    for invoice in overdue:
        if invoice.student.status != StudentStatus.ACTIVE or invoice.balance <= 0:
            continue
        entry = per_student.setdefault(invoice.student_id, {"student": invoice.student, "due": Decimal(0), "titles": [], "since": invoice.due_date})
        entry["due"] += invoice.balance
        entry["titles"].append(invoice.title)
    items = [
        (
            e["student"],
            f"{tenant.name}: Fee reminder for {e['student'].full_name}. Amount due: {tenant.currency} {e['due']:,.0f} "
            f"({', '.join(e['titles'][:3])}{'…' if len(e['titles']) > 3 else ''}), due since {e['since']:%d %b %Y}. "
            "Please pay at the school office or online in the app. Thank you.",
            f"fee:{sid}:{today}",
        )
        for sid, e in per_student.items()
    ]
    return queue_and_send(tenant, items, Kind.FEE, user)


def payment_alert(payment, user=None):
    """Thank the parent for a fee payment, with the receipt number and what is still due on the bill."""
    tenant = payment.tenant
    if not alerts_enabled(tenant) or not settings_for(tenant).payment_alerts:
        return []
    invoice = payment.invoice
    paid = sum(p.amount for p in invoice.payments.all() if p.receipt_number <= payment.receipt_number)
    balance = invoice.total - paid
    left = f"Remaining: {tenant.currency} {balance:,.0f}." if balance > 0 else "This bill is fully paid."
    body = (
        f"{tenant.name}: Received {tenant.currency} {payment.amount:,.0f} for {invoice.student.full_name} "
        f"({invoice.title}) on {payment.date:%d %b %Y}, receipt No. {payment.receipt_number}. {left} Thank you."
    )
    return queue_and_send(tenant, [(invoice.student, body, f"pay:{payment.id}")], Kind.PAYMENT, user)


def result_alerts(exam, user=None):
    """Each student's result in a newly published exam."""
    from apps.exams.results import section_results

    tenant = exam.tenant
    if not alerts_enabled(tenant) or not settings_for(tenant).result_alerts:
        return []
    items = []
    sections = Section.objects.filter(tenant=tenant, session=exam.session, program__in=exam.programs.all()).select_related("program")
    students = {e.student_id: e.student for e in Enrollment.objects.filter(section__in=sections).select_related("student")}
    for section in sections:
        for row in section_results(exam, section)["students"]:
            if row["result"] == "incomplete" or row["student"] not in students:
                continue
            position = f", position {row['position']}" if row["position"] else ""
            items.append((
                students[row["student"]],
                f"{tenant.name}: {row['full_name']}'s {exam.name} result: {row['percentage']}%, grade {row['grade']}, "
                f"{'Pass' if row['result'] == 'pass' else 'Fail'}{position}. See the report card in the app.",
                f"result:{exam.id}:{row['student']}",
            ))
    return queue_and_send(tenant, items, Kind.RESULT, user)


def homework_alerts(homework, user=None):
    tenant = homework.tenant
    if not alerts_enabled(tenant) or not settings_for(tenant).homework_alerts:
        return []
    subject = f"{homework.subject.name}: " if homework.subject else ""
    due = f" Due {homework.due_date:%d %b}." if homework.due_date else ""
    details = f" {homework.details[:200]}" if homework.details else ""
    enrollments = Enrollment.objects.filter(section=homework.section, student__status=StudentStatus.ACTIVE).select_related("student")
    items = [
        (
            e.student,
            f"{tenant.name}: Homework for {class_name(homework.section)} ({homework.date:%d %b}) — {subject}{homework.title}.{details}{due}",
            f"hw:{homework.id}:{e.student_id}",
        )
        for e in enrollments
    ]
    return queue_and_send(tenant, items, Kind.HOMEWORK, user)


def notice(tenant, text, section=None, user=None):
    """A notice to the parents of every active student (or one section's)."""
    enrollments = Enrollment.objects.filter(tenant=tenant, session__is_current=True, student__status=StudentStatus.ACTIVE).select_related("student")
    if section is not None:
        enrollments = enrollments.filter(section=section)
    return queue_and_send(tenant, [(e.student, f"{tenant.name}: {text}", "") for e in enrollments], Kind.NOTICE, user)

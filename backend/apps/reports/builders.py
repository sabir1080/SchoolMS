"""Report builders. Each returns {"title", "columns", "rows", "totals"}; the view sends it as JSON or Excel.

Columns are (label, kind) where kind is "text", "number", "money", "percent" or "date".
"""

import datetime
from decimal import Decimal

from django.db.models import Sum
from rest_framework.exceptions import ValidationError

from apps.academics.models import Section
from apps.attendance.models import AttendanceRecord, summarize
from apps.attendance.views import roll_sort_key
from apps.core.timeutils import parse_month, tenant_today
from apps.exams.models import Exam
from apps.exams.results import section_results
from apps.fees.models import Invoice, InvoiceStatus, Payment
from apps.payroll.models import Payslip
from apps.students.models import Enrollment, Student, StudentGuardian
from apps.subscriptions.features import Feature


def get_section(tenant, value, required=True):
    if not value:
        if required:
            raise ValidationError({"section": ["Choose a section."]})
        return None
    section = Section.objects.filter(tenant=tenant, pk=value).select_related("program", "session").first()
    if section is None:
        raise ValidationError({"section": ["Section not found."]})
    return section


def class_label(section):
    return f"{section.program.name} - {section.name}" if section else ""


def current_enrollments(tenant):
    return {
        e.student_id: e
        for e in Enrollment.objects.filter(tenant=tenant, session__is_current=True).select_related("section__program")
    }


def students_report(tenant, params):
    section = get_section(tenant, params.get("section"), required=False)
    status = params.get("status") or "active"
    students = Student.objects.filter(tenant=tenant)
    if status != "all":
        students = students.filter(status=status)
    enrollments = current_enrollments(tenant)
    if section:
        students = students.filter(pk__in=[sid for sid, e in enrollments.items() if e.section_id == section.id])
    guardians = {}
    for link in StudentGuardian.objects.filter(student__in=students).select_related("guardian").order_by("-is_primary", "id"):
        guardians.setdefault(link.student_id, link.guardian)
    rows = []
    for s in students:
        e, g = enrollments.get(s.id), guardians.get(s.id)
        rows.append([
            s.admission_no, s.full_name, g.name if g else "", g.phone if g else s.phone, s.get_gender_display(),
            s.date_of_birth, class_label(e.section) if e else "Not in a class", e.roll_number if e else "",
            s.get_status_display(), s.admission_date,
        ])
    rows.sort(key=lambda r: (r[6], r[7].zfill(5) if r[7].isdigit() else r[7], r[1].lower()))
    return {
        "title": f"Students{f' · {class_label(section)}' if section else ''}",
        "columns": [("Admission no", "text"), ("Name", "text"), ("Father / guardian", "text"), ("Phone", "text"), ("Gender", "text"),
                    ("Date of birth", "date"), ("Class", "text"), ("Roll", "text"), ("Status", "text"), ("Admitted", "date")],
        "rows": rows,
        "totals": [f"{len(rows)} students"],
    }


def attendance_report(tenant, params):
    section = get_section(tenant, params.get("section"))
    first, last = parse_month(params.get("month"), tenant_today(tenant))
    enrollments = sorted(Enrollment.objects.filter(section=section).select_related("student"), key=roll_sort_key)
    statuses = {}
    for sid, status in AttendanceRecord.objects.filter(section=section, date__range=(first, last)).values_list("student_id", "status"):
        statuses.setdefault(sid, []).append(status)
    rows = []
    for e in enrollments:
        s = summarize(statuses.get(e.student_id, []))
        rows.append([e.roll_number, e.student.full_name, s["total"], s["present"], s["late"], s["absent"], s["leave"], s["percentage"]])
    return {
        "title": f"Attendance · {class_label(section)} · {first:%B %Y}",
        "columns": [("Roll", "text"), ("Name", "text"), ("Days", "number"), ("Present", "number"), ("Late", "number"),
                    ("Absent", "number"), ("Leave", "number"), ("Attendance %", "percent")],
        "rows": rows,
        "totals": [],
    }


def fee_dues_report(tenant, params):
    today = tenant_today(tenant)
    enrollments = current_enrollments(tenant)
    invoices = Invoice.objects.filter(tenant=tenant, status__in=[InvoiceStatus.UNPAID, InvoiceStatus.PARTIAL]).select_related("student").order_by("due_date", "number")
    section = get_section(tenant, params.get("section"), required=False)
    rows, total = [], Decimal(0)
    for inv in invoices:
        e = enrollments.get(inv.student_id)
        if section and (not e or e.section_id != section.id):
            continue
        if inv.balance <= 0:
            continue
        overdue = (today - inv.due_date).days if inv.due_date < today else 0
        rows.append([f"INV-{inv.number:04d}", inv.student.full_name, inv.student.admission_no, class_label(e.section) if e else "",
                     inv.title, inv.due_date, inv.total, inv.paid, inv.balance, overdue])
        total += inv.balance
    return {
        "title": f"Fee dues{f' · {class_label(section)}' if section else ''} (as of {today:%d %b %Y})",
        "columns": [("Bill", "text"), ("Student", "text"), ("Adm no", "text"), ("Class", "text"), ("For", "text"), ("Due date", "date"),
                    ("Total", "money"), ("Paid", "money"), ("Balance", "money"), ("Days overdue", "number")],
        "rows": rows,
        "totals": [f"{len(rows)} bills", f"Total due: {tenant.currency} {total:,.0f}"],
    }


def fee_collection_report(tenant, params):
    first, last = parse_month(params.get("month"), tenant_today(tenant))
    payments = Payment.objects.filter(tenant=tenant, date__range=(first, last)).select_related("invoice__student").order_by("date", "receipt_number")
    rows = [[p.receipt_number, p.date, p.invoice.student.full_name, f"INV-{p.invoice.number:04d}", p.invoice.title,
             p.get_method_display(), p.reference, p.amount] for p in payments]
    total = payments.aggregate(s=Sum("amount"))["s"] or Decimal(0)
    return {
        "title": f"Fee collection · {first:%B %Y}",
        "columns": [("Receipt", "number"), ("Date", "date"), ("Student", "text"), ("Bill", "text"), ("For", "text"),
                    ("Method", "text"), ("Reference", "text"), ("Amount", "money")],
        "rows": rows,
        "totals": [f"{len(rows)} payments", f"Received: {tenant.currency} {total:,.0f}"],
    }


def exam_result_report(tenant, params):
    exam = Exam.objects.filter(tenant=tenant, pk=params.get("exam") or 0).select_related("session", "tenant").first()
    if exam is None:
        raise ValidationError({"exam": ["Choose an exam."]})
    section = get_section(tenant, params.get("section"))
    data = section_results(exam, section)
    labels = {"pass": "Pass", "fail": "Fail", "incomplete": "Incomplete"}
    rows = []
    for r in data["students"]:
        marks = ["Absent" if s["absent"] else (Decimal(s["marks"]) if s["marks"] is not None else "") for s in r["subjects"]]
        rows.append([r["position"] or "", r["roll_number"], r["full_name"], *marks, Decimal(r["obtained"]), Decimal(r["total"]),
                     Decimal(r["percentage"]) if r["percentage"] else None, r["grade"] or "", labels[r["result"]]])
    summary = data["summary"]
    return {
        "title": f"{exam.name} result · {class_label(section)}",
        "columns": [("Position", "number"), ("Roll", "text"), ("Name", "text"),
                    *[(f"{p['subject_name']} /{p['total_marks']}", "number") for p in data["papers"]],
                    ("Obtained", "number"), ("Total", "number"), ("%", "percent"), ("Grade", "text"), ("Result", "text")],
        "rows": rows,
        "totals": [f"Passed {summary['passed']} of {summary['students']}", f"Average {summary['average'] or '—'}%"],
    }


def payroll_report(tenant, params):
    first, _last = parse_month(params.get("month"), tenant_today(tenant))
    period = first.strftime("%Y-%m")
    slips = Payslip.objects.filter(tenant=tenant, period=period).select_related("employee").order_by("employee__name")
    rows = [[s.employee.name, s.employee.designation, s.basic, s.allowance, s.bonus, s.deduction, s.net,
             s.get_status_display(), s.paid_on, s.get_method_display() if s.method else ""] for s in slips]
    total = sum((s.net for s in slips), Decimal(0))
    paid = sum((s.net for s in slips if s.status == "paid"), Decimal(0))
    return {
        "title": f"Salaries · {first:%B %Y}",
        "columns": [("Name", "text"), ("Designation", "text"), ("Basic", "money"), ("Allowance", "money"), ("Bonus", "money"),
                    ("Deduction", "money"), ("Net", "money"), ("Status", "text"), ("Paid on", "date"), ("Method", "text")],
        "rows": rows,
        "totals": [f"Total: {tenant.currency} {total:,.0f}", f"Paid: {tenant.currency} {paid:,.0f}"],
    }


# name: (builder, plan feature it needs besides "reports")
REPORTS = {
    "students": (students_report, Feature.STUDENTS),
    "attendance": (attendance_report, Feature.ATTENDANCE),
    "fee-dues": (fee_dues_report, Feature.FEES),
    "fee-collection": (fee_collection_report, Feature.FEES),
    "exam-result": (exam_result_report, Feature.EXAMS),
    "payroll": (payroll_report, Feature.PAYROLL),
}


def to_json(value):
    if isinstance(value, Decimal):
        return f"{value.normalize():f}" if value != value.to_integral() else str(value.to_integral())
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    return value

"""Exam results: totals, percentage, grade, pass/fail and position for one section."""

from decimal import ROUND_HALF_UP, Decimal

from apps.attendance.models import AttendanceRecord, summarize
from apps.attendance.views import roll_sort_key
from apps.students.models import Enrollment, StudentStatus, StudentGuardian

from .models import ExamSubject, Mark, grade_for, grading_scale

PASS, FAIL, INCOMPLETE = "pass", "fail", "incomplete"


def percent(obtained, total):
    if not total:
        return None
    return (Decimal(obtained) * 100 / Decimal(total)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def text(value):
    """Decimals as strings without trailing zeros: 70.50 -> "70.5", 100.00 -> "100"."""
    if value is None:
        return None
    value = Decimal(value)
    return f"{value.normalize():f}" if value != value.to_integral() else str(value.to_integral())


def band(percentage, bands):
    found = grade_for(percentage, bands) if percentage is not None else None
    return (found.name, found.remark) if found else (None, "")


def assign_positions(rows):
    """1, 2, 2, 4 ... by percentage, among students who passed every subject."""
    ranked = sorted((r for r in rows if r["result"] == PASS), key=lambda r: -r["_pct"])
    previous, position = None, 0
    for index, row in enumerate(ranked, start=1):
        if row["_pct"] != previous:
            position, previous = index, row["_pct"]
        row["position"] = position


def section_results(exam, section):
    """Results of every active student in ``section`` for ``exam``, plus a summary."""
    bands = grading_scale(exam.tenant)
    papers = list(ExamSubject.objects.filter(exam=exam, program=section.program).select_related("subject").order_by("subject__name"))
    enrollments = sorted(
        Enrollment.objects.filter(section=section, student__status=StudentStatus.ACTIVE).select_related("student"),
        key=roll_sort_key,
    )
    student_ids = [e.student_id for e in enrollments]
    marks = {(m.student_id, m.paper_id): m for m in Mark.objects.filter(paper__in=papers, student_id__in=student_ids)}
    fathers = {}
    for link in StudentGuardian.objects.filter(student_id__in=student_ids).select_related("guardian").order_by("-is_primary", "id"):
        fathers.setdefault(link.student_id, link.guardian.name)

    grand_total = sum((p.total_marks for p in papers), Decimal(0))
    rows = []
    for e in enrollments:
        subjects, obtained, missing, failed = [], Decimal(0), 0, 0
        for p in papers:
            mark = marks.get((e.student_id, p.id))
            if mark is None:
                missing += 1
                subjects.append({"paper": p.id, "marks": None, "absent": False, "grade": None, "passed": None})
                continue
            value = Decimal(0) if mark.is_absent else mark.marks_obtained
            passed = not mark.is_absent and value >= p.pass_marks
            failed += not passed
            obtained += value
            subjects.append({
                "paper": p.id, "marks": text(None if mark.is_absent else value), "absent": mark.is_absent,
                "grade": band(percent(value, p.total_marks), bands)[0], "passed": passed,
            })
        pct = percent(obtained, grand_total) if not missing else None
        grade, remark = band(pct, bands)
        result = INCOMPLETE if missing or not papers else (FAIL if failed else PASS)
        rows.append({
            "student": e.student_id, "full_name": e.student.full_name, "admission_no": e.student.admission_no,
            "roll_number": e.roll_number, "father_name": fathers.get(e.student_id, ""), "subjects": subjects,
            "obtained": text(obtained), "total": text(grand_total), "percentage": text(pct), "grade": grade,
            "remark": remark, "result": result, "failed_subjects": failed, "position": None,
            "_pct": pct,
        })
    assign_positions(rows)
    if not exam.tenant.show_position:
        for row in rows:
            row["position"] = None
    complete = [r for r in rows if r["result"] != INCOMPLETE]
    passed = sum(r["result"] == PASS for r in rows)
    summary = {
        "students": len(rows),
        "passed": passed,
        "failed": sum(r["result"] == FAIL for r in rows),
        "incomplete": len(rows) - len(complete),
        "pass_rate": text(percent(passed, len(complete))) if complete else None,
        "average": text(percent(sum(r["_pct"] for r in complete), len(complete) * 100)) if complete else None,
        "highest": text(max(r["_pct"] for r in complete)) if complete else None,
    }
    for row in rows:
        del row["_pct"]
    return {
        "papers": [
            {"id": p.id, "subject_name": p.subject.name, "total_marks": text(p.total_marks), "pass_marks": text(p.pass_marks)}
            for p in papers
        ],
        "students": rows,
        "summary": summary,
        "grading": [{"name": b.name, "min_percentage": text(b.min_percentage), "remark": b.remark} for b in bands],
    }


def attendance_until(student, session, end_date):
    """The student's attendance in the session up to ``end_date`` (the report card's attendance line)."""
    records = AttendanceRecord.objects.filter(student=student, date__range=(session.start_date, end_date))
    return summarize(records.values_list("status", flat=True))

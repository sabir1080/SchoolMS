"""Exam results: totals, percentage, grade, pass/fail and position for one section."""

from decimal import ROUND_HALF_UP, Decimal

from apps.attendance.models import AttendanceRecord, summarize
from apps.attendance.views import roll_sort_key, section_label
from apps.core.timeutils import tenant_today
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
    return {
        "papers": [
            {"id": p.id, "subject": p.subject_id, "subject_name": p.subject.name,
             "total_marks": text(p.total_marks), "pass_marks": text(p.pass_marks)}
            for p in papers
        ],
        "students": rows,
        "summary": finish(rows, exam.tenant),
        "grading": grading_list(bands),
    }


def grading_list(bands):
    return [{"name": b.name, "min_percentage": text(b.min_percentage), "remark": b.remark} for b in bands]


def finish(rows, tenant):
    """Assign positions (if the school shows them) and return the class summary. Removes the helper "_pct"."""
    assign_positions(rows)
    if not tenant.show_position:
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
    return summary


def weighted(values):
    """Weighted average of (weight, percentage) pairs; None if any percentage is missing."""
    values = list(values)
    if not values or any(pct is None for _w, pct in values):
        return None
    total = sum(w for w, _pct in values)
    return (sum(w * pct for w, pct in values) / total).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def combined_section_results(combined, section):
    """Annual result of one section: each exam's percentage weighted by the school's weightage.

    Only exams taken by the section's class count; their weights are scaled up to 100%. A subject is
    passed when its weighted percentage reaches the institute's pass percentage.
    """
    tenant = combined.tenant
    bands = grading_scale(tenant)
    pass_pct = Decimal(tenant.pass_percentage)
    components = [c for c in combined.components.all() if section.program_id in {p.id for p in c.exam.programs.all()}]
    per_exam = [(c, section_results(c.exam, section)) for c in components]
    subjects = {}
    for _c, data in per_exam:
        for p in data["papers"]:
            subjects.setdefault(p["subject"], p["subject_name"])
    subjects = sorted(subjects.items(), key=lambda kv: kv[1])
    by_student = [{r["student"]: r for r in data["students"]} for _c, data in per_exam]
    base = per_exam[0][1]["students"] if per_exam else []

    rows = []
    for first in base:
        sid = first["student"]
        exam_cols, overall = [], []
        subject_scores = {subject_id: [] for subject_id, _n in subjects}
        for (c, data), rows_by_id in zip(per_exam, by_student):
            row = rows_by_id[sid]
            pct = Decimal(row["percentage"]) if row["percentage"] is not None else None
            exam_cols.append({"exam": c.exam_id, "percentage": text(pct)})
            overall.append((c.weight, pct))
            for paper, mark in zip(data["papers"], row["subjects"]):
                if mark["absent"]:
                    value = Decimal(0)
                elif mark["marks"] is None:
                    value = None
                else:
                    value = percent(Decimal(mark["marks"]), Decimal(paper["total_marks"]))
                subject_scores[paper["subject"]].append((c.weight, value, c.exam_id))
        subject_cols, failed, missing = [], 0, False
        for subject_id, _name in subjects:
            scores = subject_scores[subject_id]
            pct = weighted((w, v) for w, v, _e in scores)
            passed = None if pct is None else pct >= pass_pct
            missing |= pct is None
            failed += passed is False
            by_exam = {e: v for _w, v, e in scores}
            subject_cols.append({
                "subject": subject_id, "percentage": text(pct), "grade": band(pct, bands)[0], "passed": passed,
                "exams": [{"exam": c.exam_id, "percentage": text(by_exam.get(c.exam_id))} for c in components],
            })
        pct = weighted(overall)
        result = INCOMPLETE if pct is None or missing else (FAIL if failed else PASS)
        grade, remark = band(pct, bands)
        rows.append({
            **{k: first[k] for k in ("student", "full_name", "admission_no", "roll_number", "father_name")},
            "exams": exam_cols, "subjects": subject_cols, "percentage": text(pct), "grade": grade, "remark": remark,
            "result": result, "failed_subjects": failed, "position": None, "_pct": pct,
        })
    return {
        "exams": [{"id": c.exam_id, "name": c.exam.name, "weight": text(c.weight)} for c in components],
        "subjects": [{"id": subject_id, "name": name} for subject_id, name in subjects],
        "students": rows,
        "summary": finish(rows, tenant),
        "grading": grading_list(bands),
    }


def header(tenant, section):
    return {
        "institute": {"name": tenant.name, "address": tenant.address, "phone": tenant.phone, "email": tenant.email},
        "section": {
            **section_label(section),
            "class_teacher_name": section.class_teacher and (section.class_teacher.get_full_name() or section.class_teacher.username),
        },
        "show_position": tenant.show_position,
        "pass_percentage": tenant.pass_percentage,
    }


def exam_result_payload(exam, section, with_attendance=False, only_student=None):
    data = section_results(exam, section)
    if only_student is not None:
        data["students"] = [r for r in data["students"] if r["student"] == only_student]
    if with_attendance:
        end = exam.end_date or exam.session.end_date
        for row in data["students"]:
            row["attendance"] = attendance_until(row["student"], exam.session, end)
    return {
        "exam": {
            "id": exam.id, "name": exam.name, "status": exam.status, "exam_type": exam.exam_type,
            "session_name": exam.session.name, "start_date": exam.start_date, "end_date": exam.end_date,
        },
        **header(exam.tenant, section),
        **data,
    }


def combined_result_payload(combined, section, with_attendance=False, only_student=None):
    data = combined_section_results(combined, section)
    if only_student is not None:
        data["students"] = [r for r in data["students"] if r["student"] == only_student]
    if with_attendance:
        end = min(tenant_today(combined.tenant), combined.session.end_date)
        for row in data["students"]:
            row["attendance"] = attendance_until(row["student"], combined.session, end)
    return {
        "combined": {"id": combined.id, "name": combined.name, "status": combined.status, "session_name": combined.session.name},
        **header(combined.tenant, section),
        **data,
    }


def attendance_until(student, session, end_date):
    """The student's attendance in the session up to ``end_date`` (the report card's attendance line)."""
    records = AttendanceRecord.objects.filter(student=student, date__range=(session.start_date, end_date))
    return summarize(records.values_list("status", flat=True))

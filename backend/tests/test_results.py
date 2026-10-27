import pytest

from apps.academics.models import Section
from apps.accounts.models import Role
from apps.attendance.models import AttendanceRecord
from apps.exams.models import ExamSubject, Mark
from apps.students.models import Enrollment, Guardian, Student, StudentGuardian

from .test_exams import auth, create_exam, school  # noqa: F401 (fixture)


@pytest.fixture
def setup(api, admin_a, make_user, school, school_a):  # noqa: F811
    """Class 5-A with English and Mathematics (100 each, pass 33) and five students."""
    sec = Section.objects.create(tenant=school_a, program=school["c5"], session=school["session"], name="A")
    exam = create_exam(auth(api, admin_a), school).json()
    papers = {p.subject.name: p for p in ExamSubject.objects.filter(exam_id=exam["id"], program=school["c5"])}
    kids = {}
    for roll, name in enumerate(["Zara", "Ali", "Bilal", "Dua", "Eman"], start=1):
        kid = Student.objects.create(tenant=school_a, admission_no=str(roll), first_name=name, gender="female")
        Enrollment.objects.create(tenant=school_a, student=kid, section=sec, session=school["session"], roll_number=str(roll))
        kids[name] = kid
    father = Guardian.objects.create(tenant=school_a, name="Raza Khan")
    StudentGuardian.objects.create(student=kids["Zara"], guardian=father, is_primary=True)

    def mark(name, subject, value=None, absent=False):
        Mark.objects.create(tenant=school_a, paper=papers[subject], student=kids[name], section=sec,
                            marks_obtained=value, is_absent=absent)

    mark("Zara", "English", 90), mark("Zara", "Mathematics", "95.5")      # 92.75% A+
    mark("Ali", "English", 80), mark("Ali", "Mathematics", 70)            # 75% B, position 2
    mark("Bilal", "English", 70), mark("Bilal", "Mathematics", 80)        # 75% tie -> position 2
    mark("Dua", "English", 95), mark("Dua", "Mathematics", 20)            # fails Maths
    mark("Eman", "English", 60)                                           # Maths missing -> incomplete
    return {"exam": exam, "sec": sec, "kids": kids, "papers": papers}


def results(api, s):
    return api.get(f"/api/exams/{s['exam']['id']}/results/?section={s['sec'].pk}")


def test_results_totals_grades_positions(api, admin_a, setup):
    body = results(auth(api, admin_a), setup).json()
    assert [p["subject_name"] for p in body["papers"]] == ["English", "Mathematics"]
    rows = {r["full_name"]: r for r in body["students"]}
    zara = rows["Zara"]
    assert (zara["obtained"], zara["total"], zara["percentage"], zara["grade"], zara["result"], zara["position"]) == (
        "185.5", "200", "92.75", "A+", "pass", 1
    )
    assert zara["remark"] == "Outstanding" and zara["father_name"] == "Raza Khan"
    assert zara["subjects"][1] == {"paper": setup["papers"]["Mathematics"].pk, "marks": "95.5", "absent": False, "grade": "A+", "passed": True}
    assert (rows["Ali"]["position"], rows["Bilal"]["position"]) == (2, 2)
    assert (rows["Dua"]["result"], rows["Dua"]["position"], rows["Dua"]["failed_subjects"]) == ("fail", None, 1)
    assert rows["Dua"]["subjects"][1]["passed"] is False
    assert (rows["Eman"]["result"], rows["Eman"]["percentage"], rows["Eman"]["position"]) == ("incomplete", None, None)
    assert body["summary"] == {"students": 5, "passed": 3, "failed": 1, "incomplete": 1, "pass_rate": "75",
                               "average": "75.06", "highest": "92.75"}
    assert body["show_position"] is True and body["institute"]["name"]


def test_absent_fails_the_subject(api, admin_a, setup):
    Mark.objects.filter(student=setup["kids"]["Ali"], paper=setup["papers"]["English"]).update(marks_obtained=None, is_absent=True)
    rows = {r["full_name"]: r for r in results(auth(api, admin_a), setup).json()["students"]}
    ali = rows["Ali"]
    assert ali["result"] == "fail" and ali["obtained"] == "70" and ali["subjects"][0]["absent"] is True
    assert rows["Bilal"]["position"] == 2  # positions move up when Ali fails


def test_position_hidden_when_school_turns_it_off(api, admin_a, setup, school_a):
    school_a.show_position = False
    school_a.save()
    body = results(auth(api, admin_a), setup).json()
    assert body["show_position"] is False
    assert all(r["position"] is None for r in body["students"])


def test_report_card_attendance(api, admin_a, setup, school_a):
    zara = setup["kids"]["Zara"]
    for day, status in [("2026-09-01", "present"), ("2026-09-02", "absent"), ("2026-09-03", "leave"), ("2026-09-30", "present")]:
        AttendanceRecord.objects.create(tenant=school_a, student=zara, section=setup["sec"], date=day, status=status)
    body = auth(api, admin_a).get(f"/api/exams/{setup['exam']['id']}/results/?section={setup['sec'].pk}&attendance=1").json()
    att = next(r for r in body["students"] if r["full_name"] == "Zara")["attendance"]
    assert (att["total"], att["present"], att["absent"], att["percentage"]) == (3, 1, 1, 50.0)  # up to exam end 25 Sep


def test_results_access(api, admin_b, make_user, setup, school_a):
    s = setup
    teacher = make_user("t", Role.TEACHER, school_a)
    assert results(auth(api, teacher), s).status_code == 403
    s["sec"].class_teacher = teacher
    s["sec"].save()
    body = results(auth(api, teacher), s).json()
    assert body["section"]["class_teacher_name"] == "t"
    assert results(auth(api, make_user("p", Role.PARENT, school_a)), s).status_code == 403
    assert results(auth(api, admin_b), s).status_code == 404

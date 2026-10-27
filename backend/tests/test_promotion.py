import pytest

from apps.academics.models import AcademicSession, Program, Section, Subject
from apps.accounts.models import Role
from apps.exams.models import Exam, ExamSubject, Mark
from apps.students.models import Enrollment, Student


def auth(api, user):
    api.force_authenticate(user)
    return api


@pytest.fixture
def pr(make_user, school_a):
    old = AcademicSession.objects.create(tenant=school_a, name="2026-27", start_date="2026-04-01", end_date="2027-03-31", is_current=True)
    new = AcademicSession.objects.create(tenant=school_a, name="2027-28", start_date="2027-04-01", end_date="2028-03-31")
    c4, c5 = Program.objects.create(tenant=school_a, name="Class 4", sort_order=1), Program.objects.create(tenant=school_a, name="Class 5", sort_order=2)
    eng = Subject.objects.create(tenant=school_a, name="English")
    c4.subjects.set([eng])
    a = Section.objects.create(tenant=school_a, program=c4, session=old, name="A")
    c5a = Section.objects.create(tenant=school_a, program=c5, session=old, name="A")
    kids = {}
    for roll, name in enumerate(["Zara", "Ali", "Bilal", "Dua"], start=1):
        kid = Student.objects.create(tenant=school_a, admission_no=str(roll), first_name=name, gender="female",
                                     user=make_user(name.lower(), Role.STUDENT, school_a) if name == "Dua" else None)
        Enrollment.objects.create(tenant=school_a, student=kid, section=a, session=old, roll_number=str(roll))
        kids[name] = kid
    senior = Student.objects.create(tenant=school_a, admission_no="9", first_name="Senior", gender="male")
    Enrollment.objects.create(tenant=school_a, student=senior, section=c5a, session=old)
    # published exam: Ali fails
    exam = Exam.objects.create(tenant=school_a, session=old, name="Final", status="published")
    exam.programs.set([c4])
    paper = ExamSubject.objects.create(tenant=school_a, exam=exam, program=c4, subject=eng, total_marks=100, pass_marks=33)
    for name, value in (("Zara", 80), ("Ali", 20), ("Bilal", 60), ("Dua", 50)):
        Mark.objects.create(tenant=school_a, paper=paper, student=kids[name], section=a, marks_obtained=value)
    return {"old": old, "new": new, "c4": c4, "c5": c5, "a": a, "c5a": c5a, "kids": kids, "senior": senior}


def test_suggestions_from_results(api, admin_a, pr):
    body = auth(api, admin_a).get(f"/api/students/promotion/?section={pr['a'].pk}&to_session={pr['new'].pk}").json()
    assert body["next_program"]["name"] == "Class 5" and body["result_source"] == "Final"
    assert body["promote_to"] == "Class 5 - A" and body["promote_to_new"] is True and body["repeat_in"] == "Class 4 - A"
    assert {s["full_name"]: s["suggested"] for s in body["students"]} == {"Zara": "promote", "Ali": "repeat", "Bilal": "promote", "Dua": "promote"}
    assert body["students"][1]["result"] == "fail"
    last = auth(api, admin_a).get(f"/api/students/promotion/?section={pr['c5a'].pk}&to_session={pr['new'].pk}").json()
    assert last["next_program"] is None and last["students"][0]["suggested"] == "graduated"


def test_apply_decisions(api, admin_a, pr):
    api = auth(api, admin_a)
    k = pr["kids"]
    decisions = [{"student": k["Zara"].pk, "action": "promote"}, {"student": k["Ali"].pk, "action": "repeat"},
                 {"student": k["Bilal"].pk, "action": "left"}, {"student": k["Dua"].pk, "action": "promote"}]
    res = api.post("/api/students/promotion/", {"section": pr["a"].pk, "to_session": pr["new"].pk, "decisions": decisions}, format="json")
    assert res.status_code == 200, res.json()
    assert res.json() == {"promote": 2, "repeat": 1, "left": 1, "graduated": 0, "skip": 0}
    zara = Enrollment.objects.get(student=k["Zara"], session=pr["new"])
    assert (zara.section.program.name, zara.section.name, zara.roll_number) == ("Class 5", "A", "1")
    assert Enrollment.objects.get(student=k["Ali"], session=pr["new"]).section.program == pr["c4"]
    k["Bilal"].refresh_from_db()
    assert k["Bilal"].status == "left" and not Enrollment.objects.filter(student=k["Bilal"], session=pr["new"]).exists()
    assert Enrollment.objects.filter(student=k["Zara"], session=pr["old"]).exists()  # last year's record stays
    # running again moves, doesn't duplicate
    api.post("/api/students/promotion/", {"section": pr["a"].pk, "to_session": pr["new"].pk, "decisions": [{"student": k["Zara"].pk, "action": "repeat"}]}, format="json")
    assert Enrollment.objects.filter(student=k["Zara"], session=pr["new"]).count() == 1
    assert Enrollment.objects.get(student=k["Zara"], session=pr["new"]).section.program == pr["c4"]
    body = api.get(f"/api/students/promotion/?section={pr['a'].pk}&to_session={pr['new'].pk}").json()
    assert body["promote_to_new"] is False
    assert next(s for s in body["students"] if s["full_name"] == "Zara")["already"] == "Class 4 - A"


def test_graduate_and_validation(api, admin_a, pr):
    api = auth(api, admin_a)
    base = {"section": pr["c5a"].pk, "to_session": pr["new"].pk}
    res = api.post("/api/students/promotion/", {**base, "decisions": [{"student": pr["senior"].pk, "action": "promote"}]}, format="json")
    assert "last class" in str(res.json())
    assert api.post("/api/students/promotion/", {**base, "decisions": [{"student": pr["senior"].pk, "action": "graduated"}]}, format="json").status_code == 200
    pr["senior"].refresh_from_db()
    assert pr["senior"].status == "graduated"
    assert api.post("/api/students/promotion/", {**base, "decisions": [{"student": pr["kids"]["Zara"].pk, "action": "promote"}]}, format="json").status_code == 400
    assert api.get(f"/api/students/promotion/?section={pr['a'].pk}&to_session={pr['old'].pk}").status_code == 400


def test_left_student_login_is_disabled(api, admin_a, pr):
    dua = pr["kids"]["Dua"]
    auth(api, admin_a).post("/api/students/promotion/", {"section": pr["a"].pk, "to_session": pr["new"].pk,
                                                       "decisions": [{"student": dua.pk, "action": "left"}]}, format="json")
    dua.user.refresh_from_db()
    assert dua.user.is_active is False


def test_promotion_access(api, admin_b, make_user, pr, school_a):
    assert auth(api, make_user("t", Role.TEACHER, school_a)).get(f"/api/students/promotion/?section={pr['a'].pk}&to_session={pr['new'].pk}").status_code == 403
    assert auth(api, admin_b).get(f"/api/students/promotion/?section={pr['a'].pk}&to_session={pr['new'].pk}").status_code == 400

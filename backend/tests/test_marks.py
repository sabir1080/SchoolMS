import pytest

from apps.academics.models import Section
from apps.accounts.models import Role
from apps.exams.models import ExamSubject, Mark
from apps.students.models import Enrollment, Student

from .test_exams import auth, create_exam, school  # noqa: F401 (fixture)


@pytest.fixture
def setup(api, admin_a, make_user, school, school_a):  # noqa: F811
    sec_a = Section.objects.create(tenant=school_a, program=school["c5"], session=school["session"], name="A")
    sec_b = Section.objects.create(tenant=school_a, program=school["c5"], session=school["session"], name="B")
    teacher = make_user("sana", Role.TEACHER, school_a)
    sec_a.class_teacher = teacher
    sec_a.save()
    kids = []
    for i, name in enumerate(["Zara", "Ali", "Bilal"], start=1):
        kid = Student.objects.create(tenant=school_a, admission_no=str(i), first_name=name, gender="male")
        Enrollment.objects.create(tenant=school_a, student=kid, section=sec_a, session=school["session"], roll_number=str(i))
        kids.append(kid)
    other = Student.objects.create(tenant=school_a, admission_no="9", first_name="Other", gender="male")
    Enrollment.objects.create(tenant=school_a, student=other, section=sec_b, session=school["session"])
    exam = create_exam(auth(api, admin_a), school).json()
    api.patch(f"/api/exams/{exam['id']}/", {"status": "marks_open"}, format="json")
    maths = ExamSubject.objects.get(exam_id=exam["id"], program=school["c5"], subject=school["maths"])
    return {"exam": exam, "a": sec_a, "b": sec_b, "teacher": teacher, "kids": kids, "other": other, "maths": maths}


def url(s, suffix=""):
    return f"/api/exams/{s['exam']['id']}/marks/{suffix}"


def put(api, s, entries, section=None, paper=None):
    data = {"section": (section or s["a"]).pk, "paper": (paper or s["maths"]).pk, "entries": entries}
    return api.put(url(s), data, format="json")


def test_sheet_lists_students_in_roll_order(api, admin_a, setup):
    s = setup
    body = auth(api, admin_a).get(url(s) + f"?section={s['a'].pk}&paper={s['maths'].pk}").json()
    assert [r["full_name"] for r in body["students"]] == ["Zara", "Ali", "Bilal"]
    assert body["can_enter"] is True
    assert body["paper"]["subject_name"] == "Mathematics"
    assert all(r["marks"] is None and r["absent"] is False for r in body["students"])


def test_save_marks_absent_and_clear(api, admin_a, setup):
    s = setup
    zara, ali, bilal = s["kids"]
    api = auth(api, admin_a)
    res = put(api, s, [{"student": zara.pk, "marks": "88.5"}, {"student": ali.pk, "absent": True}, {"student": bilal.pk, "marks": None}])
    assert res.status_code == 200, res.json()
    rows = {r["student"]: r for r in res.json()["students"]}
    assert rows[zara.pk]["marks"] == "88.50"
    assert rows[ali.pk]["absent"] is True and rows[ali.pk]["marks"] is None
    assert rows[bilal.pk]["marks"] is None
    assert Mark.objects.count() == 2
    assert Mark.objects.get(student=zara).entered_by == admin_a
    # change and clear
    res = put(api, s, [{"student": zara.pk, "marks": None}, {"student": ali.pk, "marks": 40}])
    rows = {r["student"]: r for r in res.json()["students"]}
    assert rows[zara.pk]["marks"] is None and rows[ali.pk]["marks"] == "40.00" and rows[ali.pk]["absent"] is False
    assert Mark.objects.count() == 1


def test_marks_validation(api, admin_a, setup):
    s = setup
    api = auth(api, admin_a)
    res = put(api, s, [{"student": s["kids"][0].pk, "marks": 101}])
    assert res.status_code == 400
    assert res.json()["entries"] == ["Zara: marks cannot be more than 100."]
    assert put(api, s, [{"student": s["kids"][0].pk, "marks": -1}]).status_code == 400
    assert put(api, s, [{"student": s["other"].pk, "marks": 50}]).status_code == 400  # not in section A
    assert put(api, s, [{"student": s["kids"][0].pk, "marks": 5}, {"student": s["kids"][0].pk, "marks": 6}]).status_code == 400
    urdu6 = ExamSubject.objects.get(exam_id=s["exam"]["id"], subject__name="Urdu")  # Class 6 paper
    assert put(api, s, [], paper=urdu6).status_code == 400
    assert Mark.objects.count() == 0


def test_marks_only_while_entry_open(api, admin_a, setup):
    s = setup
    api = auth(api, admin_a)
    entry = [{"student": s["kids"][0].pk, "marks": 50}]
    for status in ("draft", "published"):
        api.patch(f"/api/exams/{s['exam']['id']}/", {"status": status}, format="json")
        res = put(api, s, entry)
        assert res.status_code == 400 and "closed" in str(res.json())
        assert api.get(url(s) + f"?section={s['a'].pk}&paper={s['maths'].pk}").json()["can_enter"] is False


def test_teacher_enters_marks_for_own_section_only(api, setup):
    s = setup
    api = auth(api, s["teacher"])
    assert put(api, s, [{"student": s["kids"][0].pk, "marks": 70}]).status_code == 200
    assert put(api, s, [{"student": s["other"].pk, "marks": 70}], section=s["b"]).status_code == 403
    progress = api.get(url(s, "progress/")).json()
    assert [sec["name"] for sec in progress["sections"]] == ["A"]


def test_progress_counts(api, admin_a, setup):
    s = setup
    api = auth(api, admin_a)
    put(api, s, [{"student": s["kids"][0].pk, "marks": 70}, {"student": s["kids"][1].pk, "absent": True}])
    body = api.get(url(s, "progress/")).json()
    assert body["can_enter"] is True
    a = next(sec for sec in body["sections"] if sec["name"] == "A")
    assert a["student_count"] == 3
    counts = {p["subject_name"]: p["entered"] for p in a["papers"]}
    assert counts == {"English": 0, "Mathematics": 2}
    assert len(body["sections"]) == 2  # Class 6 has no sections


def test_papers_with_marks_are_protected(api, admin_a, setup, school):  # noqa: F811
    s = setup
    api = auth(api, admin_a)
    put(api, s, [{"student": s["kids"][0].pk, "marks": 80}])
    exam_id = s["exam"]["id"]
    res = api.put(f"/api/exams/{exam_id}/papers/", {"program": school["c5"].pk, "papers": [], "remove": [s["maths"].pk]}, format="json")
    assert res.status_code == 400 and "already has marks" in str(res.json())
    res = api.put(f"/api/exams/{exam_id}/papers/", {"program": school["c5"].pk, "papers": [{"id": s["maths"].pk, "total_marks": 75, "pass_marks": 25}]}, format="json")
    assert res.status_code == 400 and "80 marks" in str(res.json())
    res = api.patch(f"/api/exams/{exam_id}/", {"programs": [school["c6"].pk]}, format="json")
    assert res.status_code == 400
    assert api.delete(f"/api/exams/{exam_id}/").status_code == 400
    assert ExamSubject.objects.filter(exam_id=exam_id, program=school["c5"]).count() == 2
    # A student with marks cannot be deleted
    assert api.delete(f"/api/students/{s['kids'][0].pk}/").status_code == 400


def test_marks_isolation_and_roles(api, admin_b, make_user, setup, school_a):
    s = setup
    assert auth(api, admin_b).get(url(s, "progress/")).status_code == 404
    parent = make_user("p", Role.PARENT, school_a)
    assert auth(api, parent).get(url(s, "progress/")).status_code == 403


def test_subject_teacher_enters_only_own_subjects(api, admin_a, make_user, setup, school, school_a):  # noqa: F811
    from apps.timetable.models import Period, TimetableEntry

    s = setup
    omar = make_user("omar", Role.TEACHER, school_a)
    period = Period.objects.create(tenant=school_a, name="P1", start_time="08:00", end_time="08:40")
    TimetableEntry.objects.create(tenant=school_a, section=s["b"], day=0, period=period, subject=school["maths"], teacher=omar)
    english_b = ExamSubject.objects.get(exam_id=s["exam"]["id"], program=school["c5"], subject=school["eng"])
    api = auth(api, omar)
    progress = api.get(url(s, "progress/")).json()
    assert [(sec["name"], [p["subject_name"] for p in sec["papers"]], sec["can_see_result"]) for sec in progress["sections"]] == [
        ("B", ["Mathematics"], False)
    ]
    assert put(api, s, [{"student": s["other"].pk, "marks": 77}], section=s["b"]).status_code == 200
    res = put(api, s, [{"student": s["other"].pk, "marks": 50}], section=s["b"], paper=english_b)
    assert res.status_code == 403 and "subjects you teach" in str(res.json())
    assert api.get(url(s) + f"?section={s['b'].pk}&paper={english_b.pk}").status_code == 403
    assert put(api, s, [{"student": s["kids"][0].pk, "marks": 50}]).status_code == 403  # section A: not his
    assert api.get(f"/api/exams/{s['exam']['id']}/results/?section={s['b'].pk}").status_code == 403
    # the class teacher still sees every subject and the result
    api = auth(api, s["teacher"])
    sec_a = api.get(url(s, "progress/")).json()["sections"][0]
    assert sec_a["can_see_result"] is True and len(sec_a["papers"]) == 2

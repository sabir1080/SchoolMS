
import pytest

from apps.academics.models import AcademicSession, Program, Section, Subject
from apps.accounts.models import Role
from apps.exams.models import ExamSubject, GradeBand, grade_for, grading_scale
from apps.students.models import Enrollment, Guardian, Student, StudentGuardian


def auth(api, user):
    api.force_authenticate(user)
    return api


@pytest.fixture
def school(school_a):
    session = AcademicSession.objects.create(tenant=school_a, name="2026-27", start_date="2026-04-01", end_date="2027-03-31", is_current=True)
    eng, maths, urdu = (Subject.objects.create(tenant=school_a, name=n) for n in ("English", "Mathematics", "Urdu"))
    c5 = Program.objects.create(tenant=school_a, name="Class 5", sort_order=1)
    c6 = Program.objects.create(tenant=school_a, name="Class 6", sort_order=2)
    c5.subjects.set([eng, maths])
    c6.subjects.set([eng, maths, urdu])
    return {"session": session, "c5": c5, "c6": c6, "eng": eng, "maths": maths, "urdu": urdu}


def create_exam(api, school, **extra):
    data = {"session": school["session"].pk, "name": "First Term", "exam_type": "term",
            "start_date": "2026-09-15", "end_date": "2026-09-25", "programs": [school["c5"].pk, school["c6"].pk], **extra}
    return api.post("/api/exams/", data, format="json")


# --- Grading -----------------------------------------------------------------------

def test_default_grading_scale(api, admin_a, school):
    bands = auth(api, admin_a).get("/api/exams/grading/").json()
    assert [b["name"] for b in bands] == ["A+", "A", "B", "C", "D", "E", "F"]
    scale = grading_scale(school["c5"].tenant)
    assert grade_for(95, scale).name == "A+"
    assert grade_for(33, scale).name == "E"
    assert grade_for(12, scale).name == "F"


def test_custom_grading_scale(api, admin_a, school):
    api = auth(api, admin_a)
    res = api.put("/api/exams/grading/", {"bands": [
        {"name": "Pass", "min_percentage": 40, "remark": ""}, {"name": "Distinction", "min_percentage": 75, "remark": "Well done"},
        {"name": "Fail", "min_percentage": 0, "remark": ""},
    ]}, format="json")
    assert res.status_code == 200, res.json()
    assert [b["name"] for b in res.json()] == ["Distinction", "Pass", "Fail"]
    assert GradeBand.objects.count() == 3


@pytest.mark.parametrize("bands", [
    [{"name": "A", "min_percentage": 50}],  # no 0% grade
    [{"name": "A", "min_percentage": 0}, {"name": "a", "min_percentage": 50}],  # duplicate names
    [{"name": "A", "min_percentage": 0}, {"name": "B", "min_percentage": 0}],  # same start
    [{"name": "A", "min_percentage": 0}, {"name": "B", "min_percentage": 120}],  # above 100
])
def test_grading_validation(api, admin_a, school, bands):
    assert auth(api, admin_a).put("/api/exams/grading/", {"bands": bands}, format="json").status_code == 400


def test_teacher_reads_but_cannot_change_grading(api, make_user, school, school_a):
    teacher = make_user("t", Role.TEACHER, school_a)
    api = auth(api, teacher)
    assert api.get("/api/exams/grading/").status_code == 200
    assert api.put("/api/exams/grading/", {"bands": [{"name": "A", "min_percentage": 0}]}, format="json").status_code == 403


# --- Exams -------------------------------------------------------------------------

def test_create_exam_adds_papers_from_class_subjects(api, admin_a, school):
    res = create_exam(auth(api, admin_a), school)
    assert res.status_code == 201, res.json()
    body = res.json()
    assert body["program_names"] == ["Class 5", "Class 6"]
    assert body["paper_count"] == 5  # 2 + 3
    paper = ExamSubject.objects.filter(program=school["c5"]).first()
    assert paper.total_marks == 100 and paper.pass_marks == 33


def test_pass_marks_follow_institute_pass_percentage(api, admin_a, school, school_a):
    school_a.pass_percentage = 40
    school_a.save()
    create_exam(auth(api, admin_a), school)
    assert ExamSubject.objects.first().pass_marks == 40


def test_several_exams_per_session(api, admin_a, school):
    api = auth(api, admin_a)
    for name in ("Monthly Test 1", "First Term", "Mid-Term", "Final"):
        assert create_exam(api, school, name=name).status_code == 201
    assert api.get("/api/exams/").json()["count"] == 4
    res = create_exam(api, school, name="first term")
    assert res.status_code == 400
    assert "already exists" in res.json()["name"][0]


def test_exam_validation(api, admin_a, school):
    api = auth(api, admin_a)
    assert "end_date" in create_exam(api, school, end_date="2026-09-01").json()
    assert "start_date" in create_exam(api, school, name="X", start_date="2025-01-01", end_date=None).json()
    assert "programs" in create_exam(api, school, name="Y", programs=[]).json()


def test_changing_classes_adds_and_removes_papers(api, admin_a, school):
    api = auth(api, admin_a)
    exam = create_exam(api, school, programs=[school["c5"].pk]).json()
    assert exam["paper_count"] == 2
    res = api.patch(f"/api/exams/{exam['id']}/", {"programs": [school["c6"].pk]}, format="json")
    assert res.json()["paper_count"] == 3
    assert not ExamSubject.objects.filter(program=school["c5"]).exists()


def test_edit_papers_and_datesheet(api, admin_a, school):
    api = auth(api, admin_a)
    exam = create_exam(api, school).json()
    papers = api.get(f"/api/exams/{exam['id']}/papers/?program={school['c5'].pk}").json()
    eng = next(p for p in papers if p["subject_name"] == "English")
    maths = next(p for p in papers if p["subject_name"] == "Mathematics")
    res = api.put(f"/api/exams/{exam['id']}/papers/", {"program": school["c5"].pk, "papers": [
        {"id": eng["id"], "total_marks": "75", "pass_marks": "25", "date": "2026-09-16", "start_time": "09:00"},
        {"id": maths["id"], "total_marks": "100", "pass_marks": "33", "date": "2026-09-15", "start_time": "09:00"},
    ], "add": [school["urdu"].pk]}, format="json")
    assert res.status_code == 200, res.json()
    assert [p["subject_name"] for p in res.json()[:2]] == ["Mathematics", "English"]  # date order
    assert len(res.json()) == 3
    sheet = api.get(f"/api/exams/{exam['id']}/datesheet/?program={school['c5'].pk}").json()
    assert sheet["papers"][0]["date"] == "2026-09-15"
    urdu = next(p for p in res.json() if p["subject_name"] == "Urdu")
    res = api.put(f"/api/exams/{exam['id']}/papers/", {"program": school["c5"].pk, "remove": [urdu["id"]]}, format="json")
    assert len(res.json()) == 2


def test_paper_validation(api, admin_a, school):
    api = auth(api, admin_a)
    exam = create_exam(api, school).json()
    c6_paper = ExamSubject.objects.filter(program=school["c6"]).first()
    c5_paper = ExamSubject.objects.filter(program=school["c5"]).first()
    url = f"/api/exams/{exam['id']}/papers/"
    bad_pass = {"program": school["c5"].pk, "papers": [{"id": c5_paper.id, "total_marks": "50", "pass_marks": "60"}]}
    assert api.put(url, bad_pass, format="json").status_code == 400
    wrong_class = {"program": school["c5"].pk, "papers": [{"id": c6_paper.id, "total_marks": "50", "pass_marks": "20"}]}
    assert api.put(url, wrong_class, format="json").status_code == 400
    bad_date = {"program": school["c5"].pk, "papers": [{"id": c5_paper.id, "total_marks": "50", "pass_marks": "20", "date": "2030-01-01"}]}
    assert api.put(url, bad_date, format="json").status_code == 400


def test_status_and_teacher_read_only(api, admin_a, make_user, school, school_a):
    api = auth(api, admin_a)
    exam = create_exam(api, school).json()
    assert api.patch(f"/api/exams/{exam['id']}/", {"status": "marks_open"}, format="json").json()["status"] == "marks_open"
    teacher = make_user("t", Role.TEACHER, school_a)
    api = auth(api, teacher)
    assert api.get("/api/exams/").json()["count"] == 1
    assert api.patch(f"/api/exams/{exam['id']}/", {"status": "published"}, format="json").status_code == 403
    assert api.put(f"/api/exams/{exam['id']}/papers/", {"program": school["c5"].pk}, format="json").status_code == 403


def test_subject_used_in_exam_cannot_be_deleted(api, admin_a, school):
    api = auth(api, admin_a)
    create_exam(api, school)
    assert api.delete(f"/api/academics/subjects/{school['eng'].pk}/").status_code == 400


def test_isolation_and_plan(api, admin_a, admin_b, school, school_a):
    exam = create_exam(auth(api, admin_a), school).json()
    assert auth(api, admin_b).get(f"/api/exams/{exam['id']}/").status_code == 404
    plan = school_a.subscription.plan
    plan.features = [f for f in plan.features if f != "exams"]
    plan.save()
    assert auth(api, admin_a).get("/api/exams/").status_code == 402


def test_exams_feature_added_to_plans(db):
    from apps.subscriptions.models import Plan

    assert all("exams" in p.features for p in Plan.objects.all())


def test_parent_sees_announced_datesheets(api, admin_a, make_user, school, school_a):
    api_admin = auth(api, admin_a)
    draft = create_exam(api_admin, school, name="Draft exam").json()
    announced = create_exam(api_admin, school, name="First Term").json()
    api_admin.patch(f"/api/exams/{announced['id']}/", {"status": "marks_open"}, format="json")
    section = Section.objects.create(tenant=school_a, program=school["c5"], session=school["session"], name="A")
    ali = Student.objects.create(tenant=school_a, admission_no="1", first_name="Ali", gender="male")
    Enrollment.objects.create(tenant=school_a, student=ali, section=section)
    parent = make_user("raza", Role.PARENT, school_a)
    StudentGuardian.objects.create(student=ali, guardian=Guardian.objects.create(tenant=school_a, name="R", user=parent))
    body = auth(api, parent).get(f"/api/me/exams/?student={ali.pk}").json()
    assert [e["name"] for e in body] == ["First Term"]
    assert {p["subject_name"] for p in body[0]["papers"]} == {"English", "Mathematics"}  # Class 5 papers only
    assert draft["id"] not in [e["id"] for e in body]


def test_exam_settings_on_institute(api, admin_a, school):
    api = auth(api, admin_a)
    res = api.patch("/api/institute/settings/", {"pass_percentage": 40, "show_position": False}, format="json")
    assert res.json()["pass_percentage"] == 40 and res.json()["show_position"] is False
    assert api.patch("/api/institute/settings/", {"pass_percentage": 0}, format="json").status_code == 400

import pytest

from apps.academics.models import Section
from apps.accounts.models import Role
from apps.exams.models import ExamSubject, Mark
from apps.students.models import Enrollment, Guardian, Student, StudentGuardian

from .test_exams import auth, create_exam, school  # noqa: F401 (fixture)


@pytest.fixture
def setup(api, admin_a, make_user, school, school_a):  # noqa: F811
    """Class 5-A, two exams (First Term 40%, Final 60%), English + Mathematics, three students."""
    sec = Section.objects.create(tenant=school_a, program=school["c5"], session=school["session"], name="A")
    admin = auth(api, admin_a)
    first = create_exam(admin, school, name="First Term").json()
    final = create_exam(admin, school, name="Final", start_date="2027-03-01", end_date="2027-03-10").json()
    kids = {}
    for roll, name in enumerate(["Zara", "Ali", "Bilal"], start=1):
        kid = Student.objects.create(tenant=school_a, admission_no=str(roll), first_name=name, gender="female")
        Enrollment.objects.create(tenant=school_a, student=kid, section=sec, session=school["session"], roll_number=str(roll))
        kids[name] = kid

    def marks(exam, name, english, maths):
        for subject, value in (("English", english), ("Mathematics", maths)):
            paper = ExamSubject.objects.get(exam_id=exam["id"], program=school["c5"], subject__name=subject)
            Mark.objects.create(tenant=school_a, paper=paper, student=kids[name], section=sec, marks_obtained=value)

    marks(first, "Zara", 80, 90), marks(final, "Zara", 90, 100)   # 85% and 95% -> 91%
    marks(first, "Ali", 70, 20), marks(final, "Ali", 70, 40)      # Maths 20*.4 + 40*.6 = 32% -> fail
    marks(first, "Bilal", 60, 60)                                  # Final missing -> incomplete
    return {"first": first, "final": final, "sec": sec, "kids": kids}


def create(api, school, s, **extra):  # noqa: F811
    data = {"session": school["session"].pk, "name": "Annual Result",
            "components": [{"exam": s["first"]["id"], "weight": 40}, {"exam": s["final"]["id"], "weight": 60}], **extra}
    return api.post("/api/combined-results/", data, format="json")


def test_create_and_validate(api, admin_a, setup, school):  # noqa: F811
    api = auth(api, admin_a)
    res = create(api, school, setup)
    assert res.status_code == 201, res.json()
    body = res.json()
    assert [(c["exam_name"], c["weight"]) for c in body["components"]] == [("First Term", "40"), ("Final", "60")]
    assert body["status"] == "draft"
    bad = {"components": [{"exam": setup["first"]["id"], "weight": 50}, {"exam": setup["final"]["id"], "weight": 40}]}
    assert "add up to 100" in str(create(api, school, setup, name="X", **bad).json())
    dup = {"components": [{"exam": setup["first"]["id"], "weight": 50}, {"exam": setup["first"]["id"], "weight": 50}]}
    assert create(api, school, setup, name="Y", **dup).status_code == 400
    assert create(api, school, setup).status_code == 400  # same name
    assert api.get("/api/combined-results/").json()["count"] == 1
    # an exam inside an annual result cannot be deleted (even without marks)
    Mark.objects.filter(paper__exam_id=setup["final"]["id"]).delete()
    assert "annual result" in str(api.delete(f"/api/exams/{setup['final']['id']}/").json())
    # change weights
    res = api.patch(f"/api/combined-results/{body['id']}/", {"components": [
        {"exam": setup["first"]["id"], "weight": 50}, {"exam": setup["final"]["id"], "weight": 50}]}, format="json")
    assert [c["weight"] for c in res.json()["components"]] == ["50", "50"]


def test_weighted_annual_result(api, admin_a, setup, school):  # noqa: F811
    api = auth(api, admin_a)
    combined = create(api, school, setup).json()
    body = api.get(f"/api/combined-results/{combined['id']}/results/?section={setup['sec'].pk}").json()
    assert [(e["name"], e["weight"]) for e in body["exams"]] == [("First Term", "40"), ("Final", "60")]
    assert [s["name"] for s in body["subjects"]] == ["English", "Mathematics"]
    rows = {r["full_name"]: r for r in body["students"]}
    zara = rows["Zara"]
    assert [e["percentage"] for e in zara["exams"]] == ["85", "95"]
    assert (zara["percentage"], zara["grade"], zara["result"], zara["position"]) == ("91", "A+", "pass", 1)
    assert [s["percentage"] for s in zara["subjects"]] == ["86", "96"]
    assert [e["percentage"] for e in zara["subjects"][1]["exams"]] == ["90", "100"]
    ali = rows["Ali"]
    assert {k: ali["subjects"][1][k] for k in ("percentage", "grade", "passed")} == {"percentage": "32", "grade": "F", "passed": False}
    assert (ali["result"], ali["position"]) == ("fail", None)
    assert rows["Bilal"]["result"] == "incomplete" and rows["Bilal"]["percentage"] is None
    assert body["summary"]["passed"] == 1 and body["summary"]["failed"] == 1 and body["summary"]["incomplete"] == 1
    listing = api.get(f"/api/combined-results/{combined['id']}/results/").json()
    assert [s["name"] for s in listing["sections"]] == ["A"]


def test_class_not_in_every_exam_uses_scaled_weights(api, admin_a, setup, school):  # noqa: F811
    api = auth(api, admin_a)
    # Final is only for Class 6 now, so Class 5's annual result is First Term alone (scaled to 100%).
    from apps.exams.models import Exam
    Exam.objects.get(pk=setup["final"]["id"]).programs.set([school["c6"]])
    combined = create(api, school, setup).json()
    body = api.get(f"/api/combined-results/{combined['id']}/results/?section={setup['sec'].pk}").json()
    assert [e["name"] for e in body["exams"]] == ["First Term"]
    rows = {r["full_name"]: r for r in body["students"]}
    assert rows["Zara"]["percentage"] == "85" and rows["Bilal"]["result"] == "pass"


def test_teacher_reads_only(api, make_user, admin_a, setup, school, school_a):  # noqa: F811
    combined = create(auth(api, admin_a), school, setup).json()
    teacher = make_user("t", Role.TEACHER, school_a)
    api = auth(api, teacher)
    assert api.get("/api/combined-results/").status_code == 200
    assert api.patch(f"/api/combined-results/{combined['id']}/", {"status": "published"}, format="json").status_code == 403
    assert api.get(f"/api/combined-results/{combined['id']}/results/?section={setup['sec'].pk}").status_code == 403


def test_parent_sees_only_published_results(api, admin_a, make_user, setup, school, school_a):  # noqa: F811
    admin = auth(api, admin_a)
    combined = create(admin, school, setup).json()
    parent = make_user("raza", Role.PARENT, school_a)
    zara = setup["kids"]["Zara"]
    StudentGuardian.objects.create(student=zara, guardian=Guardian.objects.create(tenant=school_a, name="R", user=parent))
    url = f"/api/me/results/?student={zara.pk}"
    assert auth(api, parent).get(url).json() == {"exams": [], "combined": []}
    admin = auth(api, admin_a)
    admin.patch(f"/api/exams/{setup['first']['id']}/", {"status": "published"}, format="json")
    admin.patch(f"/api/combined-results/{combined['id']}/", {"status": "published"}, format="json")
    body = auth(api, parent).get(url).json()
    assert [e["exam"]["name"] for e in body["exams"]] == ["First Term"]
    assert [r["full_name"] for r in body["exams"][0]["students"]] == ["Zara"]  # only their own child
    assert body["exams"][0]["students"][0]["position"] == 1
    assert body["combined"][0]["combined"]["name"] == "Annual Result"
    assert body["combined"][0]["students"][0]["percentage"] == "91"
    assert "attendance" in body["combined"][0]["students"][0]
    # another family's child is not reachable
    assert auth(api, parent).get(f"/api/me/results/?student={setup['kids']['Ali'].pk}").status_code == 404
    # the student sees their own result
    zara.user = make_user("zara", Role.STUDENT, school_a)
    zara.save()
    assert auth(api, zara.user).get("/api/me/results/").json()["exams"][0]["students"][0]["full_name"] == "Zara"

import pytest

from apps.academics.models import AcademicSession, Program, Section, Subject
from apps.accounts.models import Role
from apps.core.timeutils import tenant_today
from apps.students.models import Enrollment, Guardian, Student, StudentGuardian
from apps.timetable.models import Period, TimetableEntry


def auth(api, user):
    api.force_authenticate(user)
    return api


@pytest.fixture
def hw(make_user, school_a):
    session = AcademicSession.objects.create(tenant=school_a, name="2026-27", start_date="2026-04-01", end_date="2027-03-31", is_current=True)
    c5 = Program.objects.create(tenant=school_a, name="Class 5")
    maths = Subject.objects.create(tenant=school_a, name="Mathematics")
    a = Section.objects.create(tenant=school_a, program=c5, session=session, name="A")
    b = Section.objects.create(tenant=school_a, program=c5, session=session, name="B")
    c = Section.objects.create(tenant=school_a, program=c5, session=session, name="C")
    sana = make_user("sana", Role.TEACHER, school_a, first_name="Sana")
    omar = make_user("omar", Role.TEACHER, school_a)
    a.class_teacher = sana
    a.save()
    period = Period.objects.create(tenant=school_a, name="P1", start_time="08:00", end_time="08:40")
    TimetableEntry.objects.create(tenant=school_a, section=b, day=0, period=period, subject=maths, teacher=sana)  # teaches 5-B
    return {"a": a, "b": b, "c": c, "maths": maths, "sana": sana, "omar": omar, "today": tenant_today(school_a)}


def post(api, hw, section="a", **extra):
    data = {"section": hw[section].pk, "subject": hw["maths"].pk, "date": str(hw["today"]), "title": "Exercise 4.2 Q1-5", **extra}
    return api.post("/api/homework/", data, format="json")


def test_teacher_writes_for_own_and_taught_sections(api, hw):
    api = auth(api, hw["sana"])
    sections = api.get("/api/homework/sections/").json()
    assert [s["name"] for s in sections] == ["A", "B"]
    res = post(api, hw, details="Do in notebook", due_date=str(hw["today"]))
    assert res.status_code == 201, res.json()
    body = res.json()
    assert (body["subject_name"], body["section_name"], body["created_by_name"], body["can_edit"]) == ("Mathematics", "Class 5 - A", "Sana", True)
    assert post(api, hw, section="b").status_code == 201
    assert post(api, hw, section="c").status_code == 403
    listed = api.get(f"/api/homework/?section={hw['a'].pk}").json()
    assert [h["title"] for h in listed] == ["Exercise 4.2 Q1-5"]
    assert api.get(f"/api/homework/?section={hw['a'].pk}&date=2020-01-01").json() == []


def test_validation_and_ownership(api, admin_a, hw):
    api = auth(api, hw["sana"])
    assert post(api, hw, title="  ").status_code == 400
    assert "before" in str(post(api, hw, due_date="2020-01-01").json())
    entry = post(api, hw).json()
    # another teacher of the same section cannot change it; an admin can
    hw["a"].class_teacher = hw["omar"]
    hw["a"].save()
    period = Period.objects.first()
    TimetableEntry.objects.create(tenant=hw["a"].tenant, section=hw["a"], day=1, period=period, subject=hw["maths"], teacher=hw["sana"])
    api = auth(api, hw["omar"])
    assert api.patch(f"/api/homework/{entry['id']}/", {"title": "x"}, format="json").status_code == 403
    assert api.get(f"/api/homework/?section={hw['a'].pk}").json()[0]["can_edit"] is False
    api = auth(api, admin_a)
    assert api.patch(f"/api/homework/{entry['id']}/", {"title": "Exercise 4.3"}, format="json").json()["title"] == "Exercise 4.3"
    assert post(api, hw, section="c").status_code == 201  # admins write for any section
    assert api.delete(f"/api/homework/{entry['id']}/").status_code == 204


def test_parent_sees_child_diary(api, make_user, hw, school_a):
    post(auth(api, hw["sana"]), hw, due_date=str(hw["today"]))
    post(api, hw, section="b", title="Other section")
    kid = Student.objects.create(tenant=school_a, admission_no="1", first_name="Ali", gender="male")
    Enrollment.objects.create(tenant=school_a, student=kid, section=hw["a"], session=hw["a"].session)
    parent = make_user("raza", Role.PARENT, school_a)
    StudentGuardian.objects.create(student=kid, guardian=Guardian.objects.create(tenant=school_a, name="R", user=parent))
    body = auth(api, parent).get(f"/api/me/homework/?student={kid.pk}").json()
    assert [h["title"] for h in body["entries"]] == ["Exercise 4.2 Q1-5"]
    assert auth(api, parent).get("/api/homework/").status_code == 403


def test_isolation_and_plan(api, admin_a, admin_b, hw, school_a):
    post(auth(api, admin_a), hw)
    assert auth(api, admin_b).get("/api/homework/").json() == []
    plan = school_a.subscription.plan
    plan.features = [f for f in plan.features if f != "homework"]
    plan.save()
    assert auth(api, admin_a).get("/api/homework/").status_code == 402

import pytest

from apps.academics.models import AcademicSession, Program, Section, Subject
from apps.accounts.models import Role
from apps.students.models import Enrollment, Guardian, Student, StudentGuardian
from apps.timetable.models import Period


def auth(api, user):
    api.force_authenticate(user)
    return api


@pytest.fixture
def tt(api, admin_a, make_user, school_a):
    session = AcademicSession.objects.create(tenant=school_a, name="2026-27", start_date="2026-04-01", end_date="2027-03-31", is_current=True)
    c5 = Program.objects.create(tenant=school_a, name="Class 5")
    eng, maths = (Subject.objects.create(tenant=school_a, name=n) for n in ("English", "Mathematics"))
    a = Section.objects.create(tenant=school_a, program=c5, session=session, name="A")
    b = Section.objects.create(tenant=school_a, program=c5, session=session, name="B")
    sana = make_user("sana", Role.TEACHER, school_a, first_name="Sana", last_name="Iqbal")
    periods = auth(api, admin_a).post("/api/timetable/periods/generate/", {
        "start": "08:00", "periods": 6, "minutes": 40, "break_after": 3, "break_minutes": 20}, format="json").json()
    return {"a": a, "b": b, "eng": eng, "maths": maths, "sana": sana, "periods": periods}


def entry(api, tt, section="a", day=0, period=0, subject="eng", teacher="sana", **extra):
    data = {"section": tt[section].pk, "day": day, "period": tt["periods"][period]["id"],
            "subject": tt[subject].pk, "teacher": tt[teacher].pk if teacher else None, **extra}
    return api.post("/api/timetable/entries/", data, format="json")


def test_generate_periods_with_break(api, admin_a, tt):
    names = [(p["name"], p["start_time"][:5], p["end_time"][:5], p["is_break"]) for p in tt["periods"]]
    assert names[:5] == [
        ("Period 1", "08:00", "08:40", False), ("Period 2", "08:40", "09:20", False), ("Period 3", "09:20", "10:00", False),
        ("Break", "10:00", "10:20", True), ("Period 4", "10:20", "11:00", False),
    ]
    assert len(names) == 7
    res = auth(api, admin_a).post("/api/timetable/periods/", {"name": "Bad", "start_time": "12:00", "end_time": "11:00"}, format="json")
    assert res.status_code == 400


def test_entries_and_clashes(api, admin_a, tt):
    api = auth(api, admin_a)
    res = entry(api, tt, room="R-5")
    assert res.status_code == 201, res.json()
    body = res.json()
    assert (body["subject_name"], body["teacher_name"], body["section_name"], body["room"]) == ("English", "Sana Iqbal", "Class 5 - A", "R-5")
    assert "already has a subject" in str(entry(api, tt, subject="maths", teacher=None).json())
    clash = entry(api, tt, section="b").json()
    assert "Sana Iqbal already teaches Class 5 - A on Monday in Period 1" in str(clash)
    assert entry(api, tt, section="b", day=1).status_code == 201       # Tuesday is fine
    assert "break" in str(entry(api, tt, period=3).json())             # period index 3 is the break
    assert entry(api, tt, subject="maths", teacher=None, period=1).status_code == 201  # no teacher is allowed
    # edit moves Maths to Sana: clash-free, then clear
    entries = api.get(f"/api/timetable/entries/?section={tt['a'].pk}").json()
    assert [d["name"] for d in entries["days"]] == ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    assert len(entries["entries"]) == 2 and len(entries["periods"]) == 7
    maths = next(e for e in entries["entries"] if e["subject_name"] == "Mathematics")
    assert api.patch(f"/api/timetable/entries/{maths['id']}/", {"teacher": tt["sana"].pk}, format="json").status_code == 200
    assert api.delete(f"/api/timetable/entries/{maths['id']}/").status_code == 204
    # generating again is refused once the timetable is in use
    assert api.post("/api/timetable/periods/generate/", {"start": "08:00", "periods": 6, "minutes": 40}, format="json").status_code == 400


def test_teacher_sees_own_timetable_read_only(api, admin_a, tt):
    entry(auth(api, admin_a), tt)
    entry(api, tt, section="b", day=2, subject="maths")
    api = auth(api, tt["sana"])
    mine = api.get("/api/timetable/entries/?teacher=me").json()
    assert sorted((e["day"], e["section_name"]) for e in mine["entries"]) == [(0, "Class 5 - A"), (2, "Class 5 - B")]
    assert entry(api, tt, day=4).status_code == 403
    assert api.get(f"/api/timetable/entries/?section={tt['a'].pk}").status_code == 200


def test_working_days_setting(api, admin_a, tt, school_a):
    api = auth(api, admin_a)
    assert api.patch("/api/institute/settings/", {"working_days": "5,0,1,2,3,4"}, format="json").json()["working_days"] == "0,1,2,3,4,5"
    assert api.patch("/api/institute/settings/", {"working_days": ""}, format="json").status_code == 400
    days = api.get(f"/api/timetable/entries/?section={tt['a'].pk}").json()["days"]
    assert days[-1]["name"] == "Saturday"


def test_parent_and_student_timetable(api, admin_a, make_user, tt, school_a):
    entry(auth(api, admin_a), tt)
    kid = Student.objects.create(tenant=school_a, admission_no="1", first_name="Ali", gender="male")
    Enrollment.objects.create(tenant=school_a, student=kid, section=tt["a"], session=tt["a"].session)
    parent = make_user("raza", Role.PARENT, school_a)
    StudentGuardian.objects.create(student=kid, guardian=Guardian.objects.create(tenant=school_a, name="R", user=parent))
    body = auth(api, parent).get(f"/api/me/timetable/?student={kid.pk}").json()
    assert body["section"]["name"] == "A" and body["entries"][0]["subject_name"] == "English"
    assert auth(api, parent).get("/api/me/timetable/?student=999").status_code == 404


def test_isolation_and_plan(api, admin_a, admin_b, tt, school_a):
    assert auth(api, admin_b).get("/api/timetable/periods/").json() == []
    assert entry(auth(api, admin_b), tt).status_code == 400  # other institute's section/period ids are rejected
    plan = school_a.subscription.plan
    plan.features = [f for f in plan.features if f != "timetable"]
    plan.save()
    assert auth(api, admin_a).get("/api/timetable/periods/").status_code == 402
    assert Period.objects.filter(tenant=school_a).count() == 7

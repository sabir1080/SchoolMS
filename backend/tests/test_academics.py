import pytest

from apps.academics.models import AcademicSession, Program, Section, Subject
from apps.accounts.models import Role


def auth(api, user):
    api.force_authenticate(user)
    return api


def make_session(tenant, name="2026-27", current=False):
    return AcademicSession.objects.create(
        tenant=tenant, name=name, start_date="2026-04-01", end_date="2027-03-31", is_current=current
    )


@pytest.fixture
def teacher_a(make_user, school_a):
    return make_user("teacher_a", Role.TEACHER, school_a, first_name="Sana", last_name="Khan")


# --- Sessions --------------------------------------------------------------

def test_admin_creates_sessions_and_first_becomes_current(api, admin_a):
    api = auth(api, admin_a)
    res = api.post("/api/academics/sessions/", {"name": "2026-27", "start_date": "2026-04-01", "end_date": "2027-03-31"}, format="json")
    assert res.status_code == 201, res.json()
    assert res.json()["is_current"] is True
    res = api.post("/api/academics/sessions/", {"name": "2027-28", "start_date": "2027-04-01", "end_date": "2028-03-31"}, format="json")
    assert res.json()["is_current"] is False


def test_only_one_current_session(api, admin_a, school_a):
    s1 = make_session(school_a, "2026-27", current=True)
    s2 = make_session(school_a, "2027-28")
    res = auth(api, admin_a).patch(f"/api/academics/sessions/{s2.pk}/", {"is_current": True}, format="json")
    assert res.status_code == 200
    s1.refresh_from_db()
    assert s1.is_current is False
    assert AcademicSession.objects.filter(tenant=school_a, is_current=True).count() == 1


def test_session_dates_and_duplicate_names_validated(api, admin_a, school_a):
    make_session(school_a, "2026-27")
    api = auth(api, admin_a)
    res = api.post("/api/academics/sessions/", {"name": "x", "start_date": "2026-04-01", "end_date": "2026-01-01"}, format="json")
    assert res.status_code == 400
    assert "end_date" in res.json()
    res = api.post("/api/academics/sessions/", {"name": "2026-27 ", "start_date": "2026-04-01", "end_date": "2027-03-31"}, format="json")
    assert res.status_code == 400
    assert "already exists" in res.json()["name"][0]


# --- Programs & subjects ---------------------------------------------------

def test_bulk_create_programs_skips_existing(api, admin_a, school_a):
    Program.objects.create(tenant=school_a, name="Class 1")
    res = auth(api, admin_a).post(
        "/api/academics/programs/bulk-create/", {"names": ["Class 1", "Class 2", " Class 3 ", "class 2", ""]}, format="json"
    )
    assert res.status_code == 201, res.json()
    assert [p["name"] for p in res.json()] == ["Class 2", "Class 3"]
    assert list(Program.objects.filter(tenant=school_a).values_list("name", flat=True)) == ["Class 1", "Class 2", "Class 3"]
    # A later batch goes after the existing ones.
    auth(api, admin_a).post("/api/academics/programs/bulk-create/", {"names": ["Class 0"]}, format="json")
    assert list(Program.objects.filter(tenant=school_a).values_list("name", flat=True))[-1] == "Class 0"


def test_reorder_programs(api, admin_a, school_a, school_b):
    names = ["Nursery", "Prep 1", "Class 1", "Prep 2"]
    programs = [Program.objects.create(tenant=school_a, name=n, sort_order=i) for i, n in enumerate(names)]
    nursery, prep1, class1, prep2 = programs
    api = auth(api, admin_a)
    res = api.post(
        "/api/academics/programs/reorder/", {"ids": [nursery.pk, prep1.pk, prep2.pk, class1.pk]}, format="json"
    )
    assert res.status_code == 200, res.json()
    assert [p["name"] for p in res.json()] == ["Nursery", "Prep 1", "Prep 2", "Class 1"]
    assert [p["name"] for p in api.get("/api/academics/programs/").json()["results"]] == [
        "Nursery", "Prep 1", "Prep 2", "Class 1",
    ]


def test_reorder_needs_every_own_program_once(api, admin_a, school_a, school_b):
    a = Program.objects.create(tenant=school_a, name="A")
    b = Program.objects.create(tenant=school_a, name="B")
    other = Program.objects.create(tenant=school_b, name="X")
    api = auth(api, admin_a)
    for ids in ([a.pk], [a.pk, a.pk], [a.pk, b.pk, other.pk], [a.pk, other.pk]):
        assert api.post("/api/academics/programs/reorder/", {"ids": ids}, format="json").status_code == 400, ids


def test_teacher_cannot_reorder(api, teacher_a, school_a):
    a = Program.objects.create(tenant=school_a, name="A")
    res = auth(api, teacher_a).post("/api/academics/programs/reorder/", {"ids": [a.pk]}, format="json")
    assert res.status_code == 403


def test_program_with_subjects(api, admin_a, school_a, school_b):
    math = Subject.objects.create(tenant=school_a, name="Mathematics")
    other = Subject.objects.create(tenant=school_b, name="Physics")
    api = auth(api, admin_a)
    res = api.post("/api/academics/programs/", {"name": "Class 5", "subjects": [math.pk]}, format="json")
    assert res.status_code == 201, res.json()
    assert res.json()["subjects"] == [math.pk]
    # A subject from another institute is refused.
    res = api.post("/api/academics/programs/", {"name": "Class 6", "subjects": [other.pk]}, format="json")
    assert res.status_code == 400
    assert "subjects" in res.json()


def test_bulk_create_subjects(api, admin_a):
    res = auth(api, admin_a).post("/api/academics/subjects/bulk-create/", {"names": ["English", "Urdu"]}, format="json")
    assert res.status_code == 201
    assert len(res.json()) == 2


# --- Sections --------------------------------------------------------------

def test_admin_creates_section_with_class_teacher(api, admin_a, school_a, teacher_a):
    session = make_session(school_a, current=True)
    program = Program.objects.create(tenant=school_a, name="Class 5")
    res = auth(api, admin_a).post(
        "/api/academics/sections/",
        {"program": program.pk, "session": session.pk, "name": "A", "capacity": 40, "class_teacher": teacher_a.pk},
        format="json",
    )
    assert res.status_code == 201, res.json()
    body = res.json()
    assert body["program_name"] == "Class 5"
    assert body["session_name"] == "2026-27"
    assert body["class_teacher_name"] == "Sana Khan"


def test_duplicate_section_name_refused(api, admin_a, school_a):
    session = make_session(school_a)
    program = Program.objects.create(tenant=school_a, name="Class 5")
    Section.objects.create(tenant=school_a, program=program, session=session, name="A")
    res = auth(api, admin_a).post(
        "/api/academics/sections/", {"program": program.pk, "session": session.pk, "name": "A"}, format="json"
    )
    assert res.status_code == 400


def test_section_rejects_other_institute_objects(api, admin_a, school_a, school_b, make_user):
    session_b = make_session(school_b)
    program_b = Program.objects.create(tenant=school_b, name="Class 5")
    teacher_b = make_user("tb", Role.TEACHER, school_b)
    session_a = make_session(school_a)
    program_a = Program.objects.create(tenant=school_a, name="Class 5")
    api = auth(api, admin_a)
    res = api.post("/api/academics/sections/", {"program": program_b.pk, "session": session_b.pk, "name": "A"}, format="json")
    assert res.status_code == 400
    assert {"program", "session"} <= res.json().keys()
    res = api.post(
        "/api/academics/sections/",
        {"program": program_a.pk, "session": session_a.pk, "name": "A", "class_teacher": teacher_b.pk},
        format="json",
    )
    assert res.status_code == 400
    assert "class_teacher" in res.json()


def test_class_teacher_must_be_staff(api, admin_a, school_a, make_user):
    student = make_user("s1", Role.STUDENT, school_a)
    session = make_session(school_a)
    program = Program.objects.create(tenant=school_a, name="Class 5")
    res = auth(api, admin_a).post(
        "/api/academics/sections/",
        {"program": program.pk, "session": session.pk, "name": "A", "class_teacher": student.pk},
        format="json",
    )
    assert res.status_code == 400


def test_sections_filter_by_session_and_program(api, admin_a, school_a):
    s1 = make_session(school_a, "2026-27")
    s2 = make_session(school_a, "2027-28")
    p1 = Program.objects.create(tenant=school_a, name="Class 5")
    p2 = Program.objects.create(tenant=school_a, name="Class 6")
    Section.objects.create(tenant=school_a, program=p1, session=s1, name="A")
    Section.objects.create(tenant=school_a, program=p2, session=s1, name="A")
    Section.objects.create(tenant=school_a, program=p1, session=s2, name="A")
    api = auth(api, admin_a)
    assert api.get(f"/api/academics/sections/?session={s1.pk}").json()["count"] == 2
    assert api.get(f"/api/academics/sections/?session={s1.pk}&program={p1.pk}").json()["count"] == 1


def test_cannot_delete_program_in_use(api, admin_a, school_a):
    session = make_session(school_a)
    program = Program.objects.create(tenant=school_a, name="Class 5")
    Section.objects.create(tenant=school_a, program=program, session=session, name="A")
    api = auth(api, admin_a)
    res = api.delete(f"/api/academics/programs/{program.pk}/")
    assert res.status_code == 400
    assert "in use" in res.json()[0]
    res = api.delete(f"/api/academics/sessions/{session.pk}/")
    assert res.status_code == 400
    empty = Program.objects.create(tenant=school_a, name="Class 9")
    assert api.delete(f"/api/academics/programs/{empty.pk}/").status_code == 204


# --- Access ----------------------------------------------------------------

def test_teacher_can_read_but_not_write(api, teacher_a, school_a):
    Program.objects.create(tenant=school_a, name="Class 5")
    api = auth(api, teacher_a)
    assert api.get("/api/academics/programs/").json()["count"] == 1
    assert api.post("/api/academics/programs/", {"name": "Class 6"}, format="json").status_code == 403


def test_students_and_parents_have_no_access(api, make_user, school_a):
    student = make_user("s1", Role.STUDENT, school_a)
    assert auth(api, student).get("/api/academics/programs/").status_code == 403


def test_institutes_only_see_their_own_data(api, admin_a, school_a, school_b):
    Program.objects.create(tenant=school_a, name="Class 5")
    other = Program.objects.create(tenant=school_b, name="Secret")
    api = auth(api, admin_a)
    assert [p["name"] for p in api.get("/api/academics/programs/").json()["results"]] == ["Class 5"]
    assert api.get(f"/api/academics/programs/{other.pk}/").status_code == 404
    assert api.patch(f"/api/academics/programs/{other.pk}/", {"name": "x"}, format="json").status_code == 404


def test_plan_without_academics_is_blocked(api, admin_a, school_a):
    plan = school_a.subscription.plan
    plan.features = [f for f in plan.features if f != "academics"]
    plan.save()
    res = auth(api, admin_a).get("/api/academics/programs/")
    assert res.status_code == 402
    assert "not included in your plan" in res.json()["detail"]


def test_page_size_param(api, admin_a, school_a):
    Program.objects.bulk_create([Program(tenant=school_a, name=f"P{i}") for i in range(30)])
    api = auth(api, admin_a)
    assert len(api.get("/api/academics/programs/").json()["results"]) == 25
    assert len(api.get("/api/academics/programs/?page_size=100").json()["results"]) == 30


# --- Labels ----------------------------------------------------------------

def test_admin_sets_custom_labels(api, admin_a, school_a):
    api = auth(api, admin_a)
    res = api.patch("/api/institute/settings/", {"program_label": "Course", "section_label": "Batch"}, format="json")
    assert res.status_code == 200
    me = api.get("/api/auth/me/").json()
    assert me["tenant"]["program_label"] == "Course"
    assert me["tenant"]["section_label"] == "Batch"

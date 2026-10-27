import pytest

from apps.academics.models import AcademicSession, Program, Section
from apps.accounts.models import Role, User
from apps.students.models import Enrollment, Guardian, Student


def auth(api, user):
    api.force_authenticate(user)
    return api


@pytest.fixture
def setup(school_a):
    session = AcademicSession.objects.create(
        tenant=school_a, name="2026-27", start_date="2026-04-01", end_date="2027-03-31", is_current=True
    )
    old = AcademicSession.objects.create(tenant=school_a, name="2025-26", start_date="2025-04-01", end_date="2026-03-31")
    class5 = Program.objects.create(tenant=school_a, name="Class 5")
    class6 = Program.objects.create(tenant=school_a, name="Class 6")
    return {
        "session": session,
        "old": old,
        "class5": class5,
        "a": Section.objects.create(tenant=school_a, program=class5, session=session, name="A"),
        "b": Section.objects.create(tenant=school_a, program=class5, session=session, name="B"),
        "six": Section.objects.create(tenant=school_a, program=class6, session=session, name="A"),
        "old_a": Section.objects.create(tenant=school_a, program=class5, session=old, name="A"),
    }


def admit(api, **extra):
    data = {"first_name": "Ali", "last_name": "Raza", "gender": "male", **extra}
    return api.post("/api/students/", data, format="json")


# --- Admission ---------------------------------------------------------------

def test_admission_with_guardian_and_section(api, admin_a, setup):
    res = admit(
        auth(api, admin_a),
        date_of_birth="2016-05-10",
        id_number="35202-1234567-1",
        guardians=[{"name": "Raza Khan", "phone": "03001234567", "relation": "father"}],
        enrollment={"section": setup["a"].pk, "roll_number": "7"},
    )
    assert res.status_code == 201, res.json()
    body = res.json()
    assert body["admission_no"] == "1"
    assert body["full_name"] == "Ali Raza"
    assert body["current_enrollment"]["program_name"] == "Class 5"
    assert body["current_enrollment"]["section_name"] == "A"
    assert body["current_enrollment"]["roll_number"] == "7"
    assert body["guardian_name"] == "Raza Khan"
    assert body["guardian_links"][0]["is_primary"] is True


def test_admission_numbers_count_up_and_skip_manual_ones(api, admin_a, setup):
    api = auth(api, admin_a)
    assert admit(api).json()["admission_no"] == "1"
    assert admit(api, admission_no="2").json()["admission_no"] == "2"
    assert admit(api).json()["admission_no"] == "3"
    assert admit(api, admission_no="A-100").json()["admission_no"] == "A-100"
    assert admit(api).json()["admission_no"] == "4"
    res = admit(api, admission_no="a-100")
    assert res.status_code == 400
    assert "admission_no" in res.json()


def test_admission_numbers_are_per_institute(api, admin_a, admin_b, setup):
    assert admit(auth(api, admin_a)).json()["admission_no"] == "1"
    assert admit(auth(api, admin_b)).json()["admission_no"] == "1"


def test_siblings_share_guardian_by_phone(api, admin_a, setup):
    api = auth(api, admin_a)
    admit(api, guardians=[{"name": "Raza Khan", "phone": "03001234567"}])
    res = admit(api, first_name="Sara", gender="female", guardians=[{"name": "Raza", "phone": "03001234567"}])
    assert res.status_code == 201
    assert Guardian.objects.count() == 1
    guardian = Guardian.objects.get()
    assert guardian.name == "Raza Khan"
    assert {s.first_name for s in guardian.students.all()} == {"Ali", "Sara"}
    found = api.get("/api/guardians/?phone=03001234567").json()["results"]
    assert sorted(c["full_name"] for c in found[0]["children"]) == ["Ali Raza", "Sara Raza"]


def test_link_existing_guardian_by_id(api, admin_a, admin_b, setup, school_b):
    api = auth(api, admin_a)
    first = admit(api, guardians=[{"name": "Raza Khan", "phone": "0300"}]).json()
    gid = first["guardian_links"][0]["guardian"]["id"]
    res = admit(api, first_name="Sara", gender="female", guardians=[{"id": gid, "name": "Raza Khan", "relation": "father"}])
    assert res.status_code == 201
    assert Guardian.objects.count() == 1
    other = Guardian.objects.create(tenant=school_b, name="Other")
    res = admit(api, guardians=[{"id": other.pk, "name": "x"}])
    assert res.status_code == 400


def test_roll_number_unique_in_section(api, admin_a, setup):
    api = auth(api, admin_a)
    assert admit(api, enrollment={"section": setup["a"].pk, "roll_number": "1"}).status_code == 201
    res = admit(api, enrollment={"section": setup["a"].pk, "roll_number": "1"})
    assert res.status_code == 400
    assert Student.objects.count() == 1  # nothing half-saved
    assert admit(api, enrollment={"section": setup["b"].pk, "roll_number": "1"}).status_code == 201


def test_section_from_other_institute_refused(api, admin_b, setup):
    res = admit(auth(api, admin_b), enrollment={"section": setup["a"].pk})
    assert res.status_code == 400


def test_required_fields(api, admin_a, setup):
    res = auth(api, admin_a).post("/api/students/", {"last_name": "x"}, format="json")
    assert res.status_code == 400
    assert {"first_name", "gender"} <= res.json().keys()


# --- Enrollment ------------------------------------------------------------

def test_change_section_and_history(api, admin_a, setup):
    api = auth(api, admin_a)
    sid = admit(api, enrollment={"section": setup["old_a"].pk}).json()["id"]
    res = api.post(f"/api/students/{sid}/enroll/", {"section": setup["a"].pk, "roll_number": "3"}, format="json")
    assert res.status_code == 200
    res = api.post(f"/api/students/{sid}/enroll/", {"section": setup["six"].pk}, format="json")
    body = res.json()
    assert body["current_enrollment"]["program_name"] == "Class 6"
    assert sorted(e["session_name"] for e in body["enrollments"]) == ["2025-26", "2026-27"]
    assert Enrollment.objects.filter(student_id=sid).count() == 2


def test_remove_enrollment(api, admin_a, setup):
    api = auth(api, admin_a)
    body = admit(api, enrollment={"section": setup["a"].pk}).json()
    eid = body["enrollments"][0]["id"]
    res = api.delete(f"/api/students/{body['id']}/enrollments/{eid}/")
    assert res.status_code == 200
    assert res.json()["current_enrollment"] is None


# --- Listing & search --------------------------------------------------------

def test_search_and_filters(api, admin_a, setup):
    api = auth(api, admin_a)
    admit(api, first_name="Ali", guardians=[{"name": "Raza", "phone": "03001112223"}], enrollment={"section": setup["a"].pk})
    admit(api, first_name="Bilal", enrollment={"section": setup["six"].pk})
    admit(api, first_name="Chand", status="left")
    names = lambda url: sorted(s["first_name"] for s in api.get(url).json()["results"])  # noqa: E731
    assert names("/api/students/?search=bil") == ["Bilal"]
    assert names("/api/students/?search=1112223") == ["Ali"]
    assert names("/api/students/?search=1") == ["Ali"]  # admission no 1 + phone match, no duplicates
    assert names(f"/api/students/?program={setup['class5'].pk}") == ["Ali"]
    assert names(f"/api/students/?section={setup['six'].pk}") == ["Bilal"]
    assert names("/api/students/?status=left") == ["Chand"]
    assert names("/api/students/?unassigned=1") == ["Chand"]


def test_institutes_see_only_their_students(api, admin_a, admin_b, setup):
    sid = admit(auth(api, admin_a)).json()["id"]
    api = auth(api, admin_b)
    assert api.get("/api/students/").json()["count"] == 0
    assert api.get(f"/api/students/{sid}/").status_code == 404


# --- Edit, status, delete ------------------------------------------------------

def test_edit_guardian_with_only_name(api, admin_a, setup):
    api = auth(api, admin_a)
    sid = admit(api).json()["id"]
    res = api.patch(f"/api/students/{sid}/", {"guardians": [{"name": "Amna"}]}, format="json")
    assert res.status_code == 200, res.json()
    assert res.json()["guardian_links"][0]["is_primary"] is True


def test_edit_student_and_guardians(api, admin_a, setup):
    api = auth(api, admin_a)
    sid = admit(api, guardians=[{"name": "Raza", "phone": "0300"}]).json()["id"]
    res = api.patch(
        f"/api/students/{sid}/",
        {"address": "Street 1", "guardians": [{"name": "Amna", "phone": "0311", "relation": "mother", "is_primary": True}]},
        format="json",
    )
    assert res.status_code == 200, res.json()
    body = res.json()
    assert body["address"] == "Street 1"
    assert body["guardian_name"] == "Amna"
    assert len(body["guardian_links"]) == 1


def test_student_limit(api, admin_a, setup, school_a):
    plan = school_a.subscription.plan
    plan.max_students = 1
    plan.save()
    api = auth(api, admin_a)
    sid = admit(api).json()["id"]
    res = admit(api)
    assert res.status_code == 402
    assert "allows up to 1" in res.json()["detail"]
    assert admit(api, status="left").status_code == 201  # past students do not count
    assert api.patch(f"/api/students/{sid}/", {"status": "left"}, format="json").status_code == 200
    assert admit(api).status_code == 201
    assert api.patch(f"/api/students/{sid}/", {"status": "active"}, format="json").status_code == 402


def test_delete_student_removes_login(api, admin_a, setup):
    api = auth(api, admin_a)
    sid = admit(api).json()["id"]
    api.post(f"/api/students/{sid}/create-login/", {"username": "ali", "password": "1234"}, format="json")
    assert api.delete(f"/api/students/{sid}/").status_code == 204
    assert not User.objects.filter(username="ali").exists()


# --- Logins & portals ----------------------------------------------------------

def test_student_login_and_profile(api, admin_a, setup):
    api = auth(api, admin_a)
    sid = admit(api, enrollment={"section": setup["a"].pk, "roll_number": "5"}).json()["id"]
    res = api.post(f"/api/students/{sid}/create-login/", {"username": "ali", "password": "1234"}, format="json")
    assert res.status_code == 201, res.json()
    assert res.json()["username"] == "ali"
    assert api.post(f"/api/students/{sid}/create-login/", {"username": "ali2", "password": "1234"}, format="json").status_code == 400

    api.force_authenticate(None)
    login = api.post("/api/auth/login/", {"institute_code": "alpha", "username": "ali", "password": "1234"}, format="json")
    assert login.status_code == 200
    assert login.json()["user"]["role"] == Role.STUDENT
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {login.json()['access']}")
    me = api.get("/api/me/student/").json()
    assert me["full_name"] == "Ali Raza"
    assert me["current_enrollment"]["roll_number"] == "5"
    assert api.get("/api/students/").status_code == 403


def test_student_marked_left_cannot_log_in(api, admin_a, setup):
    api = auth(api, admin_a)
    sid = admit(api).json()["id"]
    api.post(f"/api/students/{sid}/create-login/", {"username": "ali", "password": "1234"}, format="json")
    api.patch(f"/api/students/{sid}/", {"status": "left"}, format="json")
    assert User.objects.get(username="ali").is_active is False
    api.patch(f"/api/students/{sid}/", {"status": "active"}, format="json")
    assert User.objects.get(username="ali").is_active is True


def test_parent_login_sees_all_children(api, admin_a, setup):
    api = auth(api, admin_a)
    admit(api, guardians=[{"name": "Raza Khan", "phone": "0300"}], enrollment={"section": setup["a"].pk})
    admit(api, first_name="Sara", gender="female", guardians=[{"name": "Raza Khan", "phone": "0300"}])
    gid = Guardian.objects.get().pk
    res = api.post(f"/api/guardians/{gid}/create-login/", {"username": "raza", "password": "1234"}, format="json")
    assert res.status_code == 201, res.json()
    parent = User.objects.get(username="raza")
    assert parent.role == Role.PARENT
    assert parent.first_name == "Raza"
    children = auth(api, parent).get("/api/me/children/").json()
    assert sorted(c["full_name"] for c in children) == ["Ali Raza", "Sara Raza"]
    assert api.get("/api/students/").status_code == 403


def test_login_username_must_be_free_and_follow_policy(api, admin_a, setup, school_a):
    school_a.password_policy = "strong"
    school_a.save()
    api = auth(api, admin_a)
    sid = admit(api).json()["id"]
    res = api.post(f"/api/students/{sid}/create-login/", {"username": "admin_a", "password": "Qalam2026x"}, format="json")
    assert "username" in res.json()
    res = api.post(f"/api/students/{sid}/create-login/", {"username": "ali", "password": "1234"}, format="json")
    assert "password" in res.json()


# --- Access ----------------------------------------------------------------

def test_teacher_reads_students_but_cannot_admit(api, make_user, school_a, admin_a, setup):
    admit(auth(api, admin_a))
    teacher = make_user("t1", Role.TEACHER, school_a)
    api = auth(api, teacher)
    assert api.get("/api/students/").json()["count"] == 1
    assert admit(api).status_code == 403


def test_plan_without_students_feature(api, admin_a, setup, school_a):
    plan = school_a.subscription.plan
    plan.features = [f for f in plan.features if f != "students"]
    plan.save()
    assert auth(api, admin_a).get("/api/students/").status_code == 402


def test_usage_counts_active_students(api, admin_a, setup):
    api = auth(api, admin_a)
    admit(api)
    admit(api, status="left")
    assert api.get("/api/subscription/").json()["usage"]["students"] == 1


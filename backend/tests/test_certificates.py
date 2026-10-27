import pytest

from apps.academics.models import AcademicSession, Program, Section
from apps.accounts.models import Role
from apps.students.models import Enrollment, Guardian, Student, StudentGuardian


def auth(api, user):
    api.force_authenticate(user)
    return api


@pytest.fixture
def kid(make_user, school_a):
    session = AcademicSession.objects.create(tenant=school_a, name="2026-27", start_date="2026-04-01", end_date="2027-03-31", is_current=True)
    sec = Section.objects.create(tenant=school_a, program=Program.objects.create(tenant=school_a, name="Class 5"), session=session, name="A")
    student = Student.objects.create(tenant=school_a, admission_no="17", first_name="Ahmed", last_name="Rashid", gender="male",
                                     date_of_birth="2016-05-11", admission_date="2022-04-05",
                                     user=make_user("ahmed", Role.STUDENT, school_a))
    Enrollment.objects.create(tenant=school_a, student=student, section=sec, session=session, roll_number="1")
    StudentGuardian.objects.create(student=student, guardian=Guardian.objects.create(tenant=school_a, name="Rashid Mehmood"), is_primary=True)
    return student


def test_issue_and_number_certificates(api, admin_a, kid):
    api = auth(api, admin_a)
    res = api.post("/api/certificates/", {"student": kid.pk, "kind": "bonafide", "purpose": "Passport application"}, format="json")
    assert res.status_code == 201, res.json()
    body = res.json()
    assert body["number"] == 1 and body["kind_label"] == "Bonafide (enrolment) certificate" and body["issued_on"]
    data = body["data"]
    assert (data["full_name"], data["father_name"], data["class_name"], data["roll_number"], data["date_of_birth"], data["purpose"]) == (
        "Ahmed Rashid", "Rashid Mehmood", "Class 5 - A", "1", "2016-05-11", "Passport application"
    )
    second = api.post("/api/certificates/", {"student": kid.pk, "kind": "character", "conduct": "Excellent"}, format="json").json()
    assert second["number"] == 2 and second["data"]["conduct"] == "Excellent"
    # the saved text does not change when the student's details change later
    Student.objects.filter(pk=kid.pk).update(first_name="Changed")
    assert api.get(f"/api/certificates/{body['id']}/").json()["data"]["full_name"] == "Ahmed Rashid"
    assert [c["number"] for c in api.get(f"/api/certificates/?student={kid.pk}").json()["results"]] == [2, 1]


def test_leaving_certificate(api, admin_a, kid):
    api = auth(api, admin_a)
    res = api.post("/api/certificates/", {"student": kid.pk, "kind": "leaving"}, format="json")
    assert res.status_code == 400 and "leaving_date" in res.json()
    res = api.post("/api/certificates/", {"student": kid.pk, "kind": "leaving", "leaving_date": "2027-03-31",
                                          "reason": "Family moved to Karachi", "mark_left": True}, format="json")
    assert res.status_code == 201, res.json()
    assert res.json()["data"]["leaving_date"] == "2027-03-31" and res.json()["data"]["conduct"] == "Good"
    kid.refresh_from_db()
    kid.user.refresh_from_db()
    assert kid.status == "left" and kid.user.is_active is False
    assert api.delete(f"/api/certificates/{res.json()['id']}/").status_code == 204


def test_certificate_access(api, admin_b, make_user, kid, school_a):
    assert auth(api, make_user("t", Role.TEACHER, school_a)).get("/api/certificates/").status_code == 403
    assert auth(api, admin_b).post("/api/certificates/", {"student": kid.pk, "kind": "character"}, format="json").status_code == 400

import datetime

import pytest

from apps.academics.models import AcademicSession, Program, Section
from apps.admissions.models import Application
from apps.core.timeutils import tenant_today
from apps.messaging.models import Message
from apps.students.models import Student

FORM = {
    "first_name": "Zara", "last_name": "Ahmed", "gender": "female", "date_of_birth": "2018-03-04",
    "guardian_name": "Ahmed Ali", "guardian_relation": "father", "guardian_phone": "0300-1112223",
    "address": "House 5, Lahore", "message": "Need transport info",
}


@pytest.fixture
def setup(school_a):
    today = tenant_today(school_a)
    session = AcademicSession.objects.create(
        tenant=school_a, name="Now", start_date=today - datetime.timedelta(days=10), end_date=today + datetime.timedelta(days=300), is_current=True,
    )
    c1 = Program.objects.create(tenant=school_a, name="Class 1")
    Program.objects.create(tenant=school_a, name="Old class", is_active=False)
    sec = Section.objects.create(tenant=school_a, program=c1, session=session, name="A")
    return {"c1": c1, "sec": sec}


def test_form_is_closed_until_admin_opens_it(api, admin_a, school_a, setup):
    info = api.get("/api/public/admissions/alpha/").json()
    assert info["open"] is False and info["programs"] == []
    assert api.post("/api/public/admissions/alpha/", FORM, format="json").status_code == 400
    assert api.get("/api/public/institutes/alpha/").json()["admissions_open"] is False

    api.force_authenticate(admin_a)
    assert api.patch("/api/institute/settings/", {"admissions_open": True}, format="json").json()["admissions_open"] is True
    api.force_authenticate(None)
    info = api.get("/api/public/admissions/alpha/").json()
    assert info["open"] is True and [p["name"] for p in info["programs"]] == ["Class 1"]
    assert api.get("/api/public/institutes/alpha/").json()["admissions_open"] is True
    assert api.get("/api/public/admissions/nope/").status_code == 404


def test_parent_applies_and_admin_admits(api, admin_a, school_a, setup):
    school_a.admissions_open = True
    school_a.save()
    res = api.post("/api/public/admissions/alpha/", {**FORM, "program": setup["c1"].pk}, format="json")
    assert res.status_code == 201 and res.json() == {"number": 1, "full_name": "Zara Ahmed"}
    assert api.post("/api/public/admissions/alpha/", {**FORM, "first_name": "Bilal"}, format="json").json()["number"] == 2

    api.force_authenticate(admin_a)
    apps = api.get("/api/admissions/?status=new").json()
    assert [a["full_name"] for a in apps] == ["Bilal Ahmed", "Zara Ahmed"]
    zara = next(a for a in apps if a["first_name"] == "Zara")
    assert zara["program_name"] == "Class 1" and zara["status_label"] == "New"

    res = api.post(f"/api/admissions/{zara['id']}/approve/", {"section": setup["sec"].pk, "roll_number": "7"}, format="json")
    assert res.status_code == 200, res.json()
    assert res.json()["status"] == "approved"
    student = Student.objects.get(pk=res.json()["student"])
    assert (student.full_name, student.gender, str(student.date_of_birth)) == ("Zara Ahmed", "female", "2018-03-04")
    assert student.enrollments.get().roll_number == "7"
    link = student.guardian_links.get()
    assert (link.guardian.name, link.guardian.phone, link.is_primary) == ("Ahmed Ali", "0300-1112223", True)
    assert "Online application No. 1" in student.notes
    msg = Message.objects.get(student=student)
    assert "has been given admission in Class 1 - A" in msg.body
    # Decided once only.
    assert api.post(f"/api/admissions/{zara['id']}/approve/", {}, format="json").status_code == 400

    bilal = next(a for a in apps if a["first_name"] == "Bilal")
    res = api.post(f"/api/admissions/{bilal['id']}/reject/", {"admin_note": "No seats"}, format="json").json()
    assert (res["status"], res["admin_note"], res["decided_by_name"]) == ("rejected", "No seats", "admin_a")
    assert Student.objects.count() == 1


def test_roll_number_clash_keeps_application_open(api, admin_a, school_a, setup):
    school_a.admissions_open = True
    school_a.save()
    for name in ("Zara", "Sana"):
        api.post("/api/public/admissions/alpha/", {**FORM, "first_name": name}, format="json")
    api.force_authenticate(admin_a)
    first, second = Application.objects.order_by("number")
    api.post(f"/api/admissions/{first.pk}/approve/", {"section": setup["sec"].pk, "roll_number": "1"}, format="json")
    res = api.post(f"/api/admissions/{second.pk}/approve/", {"section": setup["sec"].pk, "roll_number": "1"}, format="json")
    assert res.status_code == 400
    second.refresh_from_db()
    assert second.status == "new" and Student.objects.count() == 1


def test_form_validation_and_bots(api, school_a, setup):
    school_a.admissions_open = True
    school_a.save()
    bad = api.post("/api/public/admissions/alpha/", {**FORM, "guardian_phone": "12", "first_name": " "}, format="json").json()
    assert set(bad) == {"guardian_phone", "first_name"}
    assert api.post("/api/public/admissions/alpha/", {**FORM, "website": "spam.example"}, format="json").status_code == 400
    old = Program.objects.get(name="Old class")
    assert api.post("/api/public/admissions/alpha/", {**FORM, "program": old.pk}, format="json").status_code == 400
    assert Application.objects.count() == 0


def test_admin_only_and_tenant_isolation(api, admin_b, make_user, school_a, setup):
    from apps.accounts.models import Role

    app = Application.objects.create(tenant=school_a, number=1, first_name="Zara", gender="female", guardian_name="A", guardian_phone="03001112223")
    api.force_authenticate(admin_b)
    assert api.get("/api/admissions/").json() == []
    assert api.post(f"/api/admissions/{app.pk}/approve/", {}, format="json").status_code == 404
    api.force_authenticate(make_user("t", Role.TEACHER, school_a))
    assert api.get("/api/admissions/").status_code == 403


def test_plan_without_admissions(api, admin_a, school_a, setup):
    school_a.admissions_open = True
    school_a.save()
    plan = school_a.subscription.plan
    plan.features = [f for f in plan.features if f != "admissions"]
    plan.save()
    assert api.get("/api/public/admissions/alpha/").json()["open"] is False
    api.force_authenticate(admin_a)
    assert api.get("/api/admissions/").status_code == 402

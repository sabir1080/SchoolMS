import datetime

from django.utils import timezone

from apps.academics.models import AcademicSession, Program, Section
from apps.accounts.models import Role, User
from apps.fees.models import Invoice, InvoiceItem
from apps.recyclebin.models import DeletedItem
from apps.students.models import Enrollment, Guardian, Student, StudentGuardian


def setup(school_a):
    session = AcademicSession.objects.create(tenant=school_a, name="S", start_date="2026-04-01", end_date="2027-03-31", is_current=True)
    sec = Section.objects.create(tenant=school_a, program=Program.objects.create(tenant=school_a, name="C5"), session=session, name="A")
    return session, sec


def test_deleted_student_comes_back_with_login_and_links(api, admin_a, school_a):
    session, sec = setup(school_a)
    api.force_authenticate(admin_a)
    sid = api.post("/api/students/", {"first_name": "Zara", "gender": "female", "enrollment": {"section": sec.pk, "roll_number": "4"},
                                      "guardians": [{"name": "Ali", "phone": "0300-1234567"}]}, format="json").json()["id"]
    api.post(f"/api/students/{sid}/create-login/", {"username": "zara", "password": "1234"}, format="json")
    assert api.delete(f"/api/students/{sid}/").status_code == 204
    assert not Student.objects.filter(pk=sid).exists() and not User.objects.filter(username="zara").exists()

    bin_items = api.get("/api/recycle-bin/").json()
    assert bin_items[0]["label"].startswith("Student: Zara (Adm") and bin_items[0]["days_left"] == 30
    assert bin_items[0]["deleted_by_name"] == "admin_a"
    res = api.post(f"/api/recycle-bin/{bin_items[0]['id']}/")
    assert res.status_code == 200, res.json()
    student = Student.objects.get(pk=sid)
    assert student.user.username == "zara" and student.user.check_password("1234")
    assert Enrollment.objects.get(student=student).roll_number == "4"
    assert StudentGuardian.objects.get(student=student).guardian.name == "Ali"
    assert api.get("/api/recycle-bin/").json() == []


def test_deleted_payment_comes_back_and_bill_totals_follow(api, admin_a, school_a):
    session, sec = setup(school_a)
    kid = Student.objects.create(tenant=school_a, admission_no="1", first_name="Ali", gender="male")
    inv = Invoice.objects.create(tenant=school_a, number=1, student=kid, session=session, title="Fee", issue_date="2026-10-01", due_date="2026-10-10")
    InvoiceItem.objects.create(invoice=inv, description="Tuition", amount=3000)
    inv.refresh_totals()
    api.force_authenticate(admin_a)
    pay = api.post(f"/api/fees/invoices/{inv.pk}/payments/", {"amount": "3000", "date": "2026-10-05"}, format="json").json()["payments"][0]
    api.delete(f"/api/fees/payments/{pay['id']}/")
    inv.refresh_from_db()
    assert inv.status == "unpaid"
    item = api.get("/api/recycle-bin/").json()[0]
    assert item["label"] == "Payment: receipt 1 · Ali · PKR 3,000"
    api.post(f"/api/recycle-bin/{item['id']}/")
    inv.refresh_from_db()
    assert (inv.status, str(inv.paid)) == ("paid", "3000.00")


def test_restore_conflict_is_explained(api, admin_a, school_a):
    setup(school_a)
    api.force_authenticate(admin_a)
    sid = api.post("/api/students/", {"first_name": "Zara", "gender": "female", "admission_no": "A-1"}, format="json").json()["id"]
    api.delete(f"/api/students/{sid}/")
    api.post("/api/students/", {"first_name": "Other", "gender": "male", "admission_no": "A-1"}, format="json")
    item = api.get("/api/recycle-bin/").json()[0]
    res = api.post(f"/api/recycle-bin/{item['id']}/")
    assert res.status_code == 400 and "same number or name" in str(res.json())
    assert Student.objects.filter(tenant=school_a).count() == 1  # nothing half-restored


def test_protection_purge_delete_forever_and_access(api, admin_a, admin_b, make_user, school_a):
    session, sec = setup(school_a)
    api.force_authenticate(admin_a)
    # Still protected: a section with students cannot be deleted.
    kid = Student.objects.create(tenant=school_a, admission_no="1", first_name="Ali", gender="male")
    Enrollment.objects.create(tenant=school_a, student=kid, section=sec)
    assert api.delete(f"/api/academics/sections/{sec.pk}/").status_code == 400
    assert DeletedItem.objects.count() == 0
    # Subjects and other simple deletes go to the bin.
    sub = api.post("/api/academics/subjects/", {"name": "Art"}, format="json").json()
    api.delete(f"/api/academics/subjects/{sub['id']}/")
    items = api.get("/api/recycle-bin/").json()
    assert items[0]["label"] == "Subject: Art"
    # Older than 30 days: gone.
    old = DeletedItem.objects.get()
    DeletedItem.objects.filter(pk=old.pk).update(created_at=timezone.now() - datetime.timedelta(days=31))
    assert api.get("/api/recycle-bin/").json() == []
    assert not DeletedItem.objects.exists()
    # Delete forever.
    sub2 = api.post("/api/academics/subjects/", {"name": "Music"}, format="json").json()
    api.delete(f"/api/academics/subjects/{sub2['id']}/")
    item = api.get("/api/recycle-bin/").json()[0]
    assert api.delete(f"/api/recycle-bin/{item['id']}/").status_code == 204
    # Others cannot see or restore.
    sub3 = api.post("/api/academics/subjects/", {"name": "PT"}, format="json").json()
    api.delete(f"/api/academics/subjects/{sub3['id']}/")
    item = api.get("/api/recycle-bin/").json()[0]
    api.force_authenticate(admin_b)
    assert api.get("/api/recycle-bin/").json() == []
    assert api.post(f"/api/recycle-bin/{item['id']}/").status_code == 404
    api.force_authenticate(make_user("t", Role.TEACHER, school_a))
    assert api.get("/api/recycle-bin/").status_code == 403


def test_guardian_kept_when_shared(api, admin_a, school_a):
    """Deleting one sibling keeps the shared parent; restoring links them again."""
    setup(school_a)
    g = Guardian.objects.create(tenant=school_a, name="Raza", phone="0300")
    kids = []
    for n in ("A", "B"):
        k = Student.objects.create(tenant=school_a, admission_no=n, first_name=n, gender="male")
        StudentGuardian.objects.create(student=k, guardian=g)
        kids.append(k)
    api.force_authenticate(admin_a)
    api.delete(f"/api/students/{kids[0].pk}/")
    assert Guardian.objects.filter(pk=g.pk).exists()
    api.post(f"/api/recycle-bin/{api.get('/api/recycle-bin/').json()[0]['id']}/")
    assert set(g.students.values_list("first_name", flat=True)) == {"A", "B"}

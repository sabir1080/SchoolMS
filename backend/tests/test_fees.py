from decimal import Decimal

import pytest

from apps.academics.models import AcademicSession, Program, Section
from apps.accounts.models import Role
from apps.fees.models import FeeHead, FeeRate, Invoice, InvoiceStatus, StudentDiscount
from apps.students.models import Enrollment, Guardian, Student, StudentGuardian


def auth(api, user):
    api.force_authenticate(user)
    return api


@pytest.fixture
def school(school_a):
    session = AcademicSession.objects.create(
        tenant=school_a, name="2026-27", start_date="2026-04-01", end_date="2027-03-31", is_current=True
    )
    c5 = Program.objects.create(tenant=school_a, name="Class 5")
    c6 = Program.objects.create(tenant=school_a, name="Class 6")
    s5 = Section.objects.create(tenant=school_a, program=c5, session=session, name="A")
    s6 = Section.objects.create(tenant=school_a, program=c6, session=session, name="A")
    tuition = FeeHead.objects.create(tenant=school_a, name="Tuition Fee", frequency="monthly", sort_order=1)
    admission = FeeHead.objects.create(tenant=school_a, name="Admission Fee", frequency="one_time", sort_order=0)
    for program, t, a in [(c5, "3000", "5000"), (c6, "3500", "5000")]:
        FeeRate.objects.create(tenant=school_a, program=program, session=session, fee_head=tuition, amount=Decimal(t))
        FeeRate.objects.create(tenant=school_a, program=program, session=session, fee_head=admission, amount=Decimal(a))
    kids = {}
    for name, section in [("Ali", s5), ("Sara", s5), ("Bilal", s6)]:
        kids[name] = Student.objects.create(tenant=school_a, admission_no=name, first_name=name, gender="male")
        Enrollment.objects.create(tenant=school_a, student=kids[name], section=section)
    gone = Student.objects.create(tenant=school_a, admission_no="G", first_name="Gone", gender="male", status="left")
    Enrollment.objects.create(tenant=school_a, student=gone, section=s5)
    return {"session": session, "c5": c5, "c6": c6, "s5": s5, "s6": s6, "tuition": tuition, "admission": admission, **kids}


def generate(api, school, month="2026-10", **extra):
    return api.post(
        "/api/fees/invoices/generate/",
        {"session": school["session"].pk, "month": month, "issue_date": f"{month}-01", "due_date": f"{month}-10", **extra},
        format="json",
    )


# --- Setup -------------------------------------------------------------------

def test_fee_heads_crud_and_bulk(api, admin_a, school):
    api = auth(api, admin_a)
    res = api.post("/api/fees/heads/bulk-create/", {"names": ["Exam Fee", "Tuition Fee"]}, format="json")
    assert [h["name"] for h in res.json()] == ["Exam Fee"]
    res = api.post("/api/fees/heads/", {"name": "tuition fee"}, format="json")
    assert res.status_code == 400


def test_set_rates_for_a_class(api, admin_a, school):
    api = auth(api, admin_a)
    exam = FeeHead.objects.create(tenant=school["c5"].tenant, name="Exam Fee")
    res = api.post(
        "/api/fees/rates/",
        {"session": school["session"].pk, "program": school["c5"].pk, "rates": [
            {"fee_head": school["tuition"].pk, "amount": "3200"},
            {"fee_head": school["admission"].pk, "amount": "0"},
            {"fee_head": exam.pk, "amount": "500"},
        ]},
        format="json",
    )
    assert res.status_code == 200, res.json()
    rates = {(r["program"], r["fee_head"]): r["amount"] for r in res.json()}
    assert rates[(school["c5"].pk, school["tuition"].pk)] == "3200.00"
    assert (school["c5"].pk, school["admission"].pk) not in rates  # 0 removes it
    assert rates[(school["c6"].pk, school["tuition"].pk)] == "3500.00"  # other class untouched


# --- Generating invoices -------------------------------------------------------

def test_generate_monthly_invoices(api, admin_a, school):
    res = generate(auth(api, admin_a), school)
    assert res.status_code == 200, res.json()
    assert res.json()["created"] == 3  # left student skipped
    ali = Invoice.objects.get(student=school["Ali"])
    assert ali.title == "October 2026 fee"
    assert ali.total == Decimal("8000")  # 5000 admission + 3000 tuition
    assert [i.description for i in ali.items.all()] == ["Admission Fee", "Tuition Fee"]
    assert Invoice.objects.get(student=school["Bilal"]).total == Decimal("8500")
    assert sorted(Invoice.objects.values_list("number", flat=True)) == [1, 2, 3]


def test_generate_twice_is_safe_and_one_time_fees_charged_once(api, admin_a, school):
    api = auth(api, admin_a)
    generate(api, school)
    res = generate(api, school).json()
    assert res["created"] == 0
    assert res["already_billed"] == 3
    generate(api, school, month="2026-11")
    nov = Invoice.objects.get(student=school["Ali"], period="2026-11")
    assert nov.total == Decimal("3000")  # admission fee not charged again


def test_generate_for_selected_sections(api, admin_a, school):
    res = generate(auth(api, admin_a), school, sections=[school["s6"].pk]).json()
    assert res["created"] == 1
    assert Invoice.objects.get().student == school["Bilal"]


def test_discounts_apply(api, admin_a, school):
    api = auth(api, admin_a)
    res = api.post("/api/fees/discounts/", {
        "student": school["Sara"].pk, "fee_head": school["tuition"].pk, "discount_type": "percent", "value": "50",
        "reason": "Sibling",
    }, format="json")
    assert res.status_code == 201, res.json()
    api.post("/api/fees/discounts/", {
        "student": school["Ali"].pk, "fee_head": school["admission"].pk, "discount_type": "amount", "value": "9999",
    }, format="json")
    generate(api, school)
    sara = Invoice.objects.get(student=school["Sara"])
    assert sara.total == Decimal("6500")  # 5000 + 3000 - 1500
    ali = Invoice.objects.get(student=school["Ali"])
    assert ali.total == Decimal("3000")  # admission fully waived, never negative


def test_discount_validation(api, admin_a, school):
    api = auth(api, admin_a)
    base = {"student": school["Ali"].pk, "fee_head": school["tuition"].pk}
    assert api.post("/api/fees/discounts/", {**base, "discount_type": "percent", "value": "120"}, format="json").status_code == 400
    assert api.post("/api/fees/discounts/", {**base, "value": "0"}, format="json").status_code == 400
    assert api.post("/api/fees/discounts/", {**base, "value": "100"}, format="json").status_code == 201
    assert api.post("/api/fees/discounts/", {**base, "value": "200"}, format="json").status_code == 400


def test_fully_waived_student_gets_no_invoice(api, admin_a, school):
    for head in (school["tuition"], school["admission"]):
        StudentDiscount.objects.create(tenant=school["Ali"].tenant, student=school["Ali"], fee_head=head, discount_type="percent", value=100)
    res = generate(auth(api, admin_a), school).json()
    assert res["nothing_to_bill"] == 1
    assert not Invoice.objects.filter(student=school["Ali"]).exists()


# --- Payments ------------------------------------------------------------------

def test_partial_and_full_payment_with_receipts(api, admin_a, school):
    api = auth(api, admin_a)
    generate(api, school)
    inv = Invoice.objects.get(student=school["Ali"])
    url = f"/api/fees/invoices/{inv.pk}/payments/"
    res = api.post(url, {"amount": "3000", "date": "2026-10-05", "method": "jazzcash", "reference": "JC1"}, format="json")
    assert res.status_code == 201, res.json()
    assert res.json()["status"] == "partial"
    assert res.json()["balance"] == "5000.00"
    res = api.post(url, {"amount": "6000", "date": "2026-10-06"}, format="json")
    assert res.status_code == 400
    assert "Only 5000.00 is left" in res.json()["amount"][0]
    res = api.post(url, {"amount": "5000", "date": "2026-10-06", "method": "cash"}, format="json")
    body = res.json()
    assert body["status"] == "paid"
    assert [p["receipt_number"] for p in body["payments"]] == [1, 2]
    assert body["payments"][0]["received_by_name"] == "admin_a"


def test_delete_payment_recalculates(api, admin_a, school):
    api = auth(api, admin_a)
    generate(api, school)
    inv = Invoice.objects.get(student=school["Ali"])
    pay = api.post(f"/api/fees/invoices/{inv.pk}/payments/", {"amount": "8000", "date": "2026-10-05"}, format="json").json()
    assert pay["status"] == "paid"
    assert api.delete(f"/api/fees/payments/{pay['payments'][0]['id']}/").status_code == 204
    inv.refresh_from_db()
    assert inv.status == InvoiceStatus.UNPAID
    assert inv.paid == 0


def test_cancel_invoice_and_regenerate(api, admin_a, school):
    api = auth(api, admin_a)
    generate(api, school)
    inv = Invoice.objects.get(student=school["Ali"])
    api.post(f"/api/fees/invoices/{inv.pk}/payments/", {"amount": "100", "date": "2026-10-05"}, format="json")
    assert api.post(f"/api/fees/invoices/{inv.pk}/cancel/").status_code == 400  # has payments
    api.delete(f"/api/fees/payments/{inv.payments.get().pk}/")
    res = api.post(f"/api/fees/invoices/{inv.pk}/cancel/")
    assert res.json()["status"] == "cancelled"
    assert api.post(f"/api/fees/invoices/{inv.pk}/payments/", {"amount": "100", "date": "2026-10-05"}, format="json").status_code == 400
    # A cancelled bill no longer blocks the month, and its admission fee can be billed again.
    assert generate(api, school).json()["created"] == 1
    assert Invoice.objects.get(student=school["Ali"], status="unpaid").total == Decimal("8000")


def test_manual_invoice(api, admin_a, school):
    res = auth(api, admin_a).post("/api/fees/invoices/", {
        "student": school["Ali"].pk, "session": school["session"].pk, "title": "Annual trip",
        "issue_date": "2026-10-01", "due_date": "2026-10-15",
        "items": [{"description": "Trip", "amount": "2000", "discount": "500"}],
    }, format="json")
    assert res.status_code == 201, res.json()
    assert res.json()["total"] == "1500.00"
    assert res.json()["period"] == ""


# --- Lists and summary -----------------------------------------------------------

def test_invoice_filters(api, admin_a, school):
    api = auth(api, admin_a)
    generate(api, school)
    ali = Invoice.objects.get(student=school["Ali"])
    api.post(f"/api/fees/invoices/{ali.pk}/payments/", {"amount": "8000", "date": "2026-10-05"}, format="json")
    count = lambda q: api.get(f"/api/fees/invoices/?{q}").json()["count"]  # noqa: E731
    assert count("") == 3
    assert count("status=paid") == 1
    assert count("status=due") == 2
    assert count(f"program={school['c5'].pk}") == 2
    assert count(f"section={school['s6'].pk}") == 1
    assert count("search=bil") == 1
    assert count(f"search=INV-{ali.number:04d}") == 1
    assert count("period=2026-11") == 0


def test_summary_and_defaulters(api, admin_a, school):
    api = auth(api, admin_a)
    generate(api, school, month="2026-09")  # due 2026-09-10, in the past
    ali = Invoice.objects.get(student=school["Ali"])
    api.post(f"/api/fees/invoices/{ali.pk}/payments/", {"amount": "8000", "date": "2026-09-05"}, format="json")
    body = api.get("/api/fees/summary/?month=2026-09").json()
    assert body["billed"] == "24500.00"
    assert body["collected"] == "8000.00"
    assert body["outstanding"] == "16500.00"
    assert body["collection_percentage"] == pytest.approx(32.7)
    assert body["overdue_students"] == 2
    assert body["defaulters"][0]["full_name"] == "Bilal"  # largest balance first
    assert api.get("/api/fees/summary/?month=bad").status_code == 400


# --- Access ----------------------------------------------------------------------

def test_teacher_cannot_see_fees(api, make_user, school, school_a):
    teacher = make_user("t", Role.TEACHER, school_a)
    assert auth(api, teacher).get("/api/fees/invoices/").status_code == 403


def test_other_institute_isolated(api, admin_a, admin_b, school):
    generate(auth(api, admin_a), school)
    api = auth(api, admin_b)
    assert api.get("/api/fees/invoices/").json()["count"] == 0
    inv = Invoice.objects.first()
    assert api.get(f"/api/fees/invoices/{inv.pk}/").status_code == 404
    res = api.post("/api/fees/discounts/", {"student": school["Ali"].pk, "fee_head": school["tuition"].pk, "value": "1"}, format="json")
    assert res.status_code == 400


def test_parent_sees_child_invoices(api, admin_a, school, school_a, make_user):
    generate(auth(api, admin_a), school)
    parent = make_user("raza", Role.PARENT, school_a)
    guardian = Guardian.objects.create(tenant=school_a, name="Raza", user=parent)
    StudentGuardian.objects.create(student=school["Ali"], guardian=guardian)
    api = auth(api, parent)
    res = api.get(f"/api/me/invoices/?student={school['Ali'].pk}")
    assert res.status_code == 200
    assert res.json()[0]["total"] == "8000.00"
    assert api.get(f"/api/me/invoices/?student={school['Sara'].pk}").status_code == 404
    assert api.get("/api/fees/invoices/").status_code == 403


def test_plan_without_fees(api, admin_a, school, school_a):
    plan = school_a.subscription.plan
    plan.features = [f for f in plan.features if f != "fees"]
    plan.save()
    assert auth(api, admin_a).get("/api/fees/invoices/").status_code == 402


def test_student_with_invoice_cannot_be_deleted(api, admin_a, school):
    api = auth(api, admin_a)
    generate(api, school)
    res = api.delete(f"/api/students/{school['Ali'].pk}/")
    assert res.status_code == 400

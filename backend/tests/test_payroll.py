from apps.accounts.models import Role
from apps.payroll.models import Payslip


def auth(api, user):
    api.force_authenticate(user)
    return api


def add(api, **extra):
    data = {"name": "Sana Iqbal", "designation": "Teacher", "basic_salary": "45000", "allowance": "5000", **extra}
    return api.post("/api/payroll/employees/", data, format="json")


def test_staff_and_monthly_salaries(api, admin_a, make_user, school_a):
    api = auth(api, admin_a)
    sana_login = make_user("sana", Role.TEACHER, school_a)
    sana = add(api, user=sana_login.pk).json()
    assert sana["user_name"] == "sana"
    add(api, name="Akram", designation="Guard", basic_salary="25000", allowance="0")
    add(api, name="Old staff", basic_salary="20000", is_active=False)
    assert api.post("/api/payroll/payslips/generate/", {"period": "2026-10"}, format="json").json() == {"created": 2, "already": 0}
    assert api.post("/api/payroll/payslips/generate/", {"period": "2026-10"}, format="json").json() == {"created": 0, "already": 2}
    assert api.post("/api/payroll/payslips/generate/", {"period": "2026-13"}, format="json").status_code == 400
    body = api.get("/api/payroll/payslips/?period=2026-10").json()
    assert body["summary"] == {"count": 2, "paid_count": 0, "total": "75000.00", "paid": "0.00", "unpaid": "75000.00"}
    slip = next(s for s in body["results"] if s["employee_name"] == "Sana Iqbal")
    assert (slip["basic"], slip["allowance"], slip["net"]) == ("45000.00", "5000.00", "50000.00")
    res = api.patch(f"/api/payroll/payslips/{slip['id']}/", {"bonus": "2000", "deduction": "1500", "note": "2 days leave"}, format="json").json()
    assert (res["gross"], res["net"]) == ("52000.00", "50500.00")
    assert api.patch(f"/api/payroll/payslips/{slip['id']}/", {"deduction": "99999"}, format="json").status_code == 400
    paid = api.post(f"/api/payroll/payslips/{slip['id']}/pay/", {"date": "2026-10-31", "method": "bank", "reference": "TX1"}, format="json").json()
    assert (paid["status"], paid["method_label"]) == ("paid", "Bank deposit / transfer")
    assert "already paid" in str(api.patch(f"/api/payroll/payslips/{slip['id']}/", {"bonus": "1"}, format="json").json())
    assert api.delete(f"/api/payroll/payslips/{slip['id']}/").status_code == 400
    assert api.get("/api/payroll/payslips/?period=2026-10").json()["summary"]["paid"] == "50500.00"
    # salary changes later do not change an existing slip
    api.patch(f"/api/payroll/employees/{sana['id']}/", {"basic_salary": "50000"}, format="json")
    assert Payslip.objects.get(pk=slip["id"]).basic == 45000
    # staff with slips cannot be deleted
    assert "Active" in str(api.delete(f"/api/payroll/employees/{sana['id']}/").json())
    assert api.post(f"/api/payroll/payslips/{slip['id']}/unpay/").json()["status"] == "unpaid"
    # teacher sees own slips only
    mine = auth(api, sana_login).get("/api/me/payslips/").json()
    assert mine["linked"] is True and [s["net"] for s in mine["results"]] == ["50500.00"]
    assert auth(api, sana_login).get("/api/payroll/payslips/").status_code == 403


def test_validation_isolation_and_plan(api, admin_a, admin_b, make_user, school_a):
    api = auth(api, admin_a)
    parent = make_user("p", Role.PARENT, school_a)
    assert add(api, user=parent.pk).status_code == 400
    assert add(api, basic_salary="-5").status_code == 400
    teacher = make_user("t", Role.TEACHER, school_a)
    add(api, user=teacher.pk)
    assert "already linked" in str(add(api, name="Other", user=teacher.pk).json())
    assert auth(api, admin_b).get("/api/payroll/employees/").json() == []
    plan = school_a.subscription.plan
    plan.features = [f for f in plan.features if f != "payroll"]
    plan.save()
    assert auth(api, admin_a).get("/api/payroll/employees/").status_code == 402

import datetime
import gzip
import io
import json
import re

from django.core.files.uploadedfile import SimpleUploadedFile
from openpyxl import load_workbook

from apps.accounts.models import Role, User
from apps.backups import institute
from apps.backups.models import InstituteSnapshot
from apps.backups.services import create_backup
from apps.fees.models import Invoice, Payment
from apps.messaging.models import MessagingSettings
from apps.payments.models import GatewayAccount
from apps.students.models import Student
from apps.tenants.demo import seed_demo
from apps.tenants.models import Tenant

TODAY = datetime.date(2026, 10, 14)


def rows_of(tenant):
    """Everything that belongs to an institute, comparable before/after (times to the millisecond: the full
    platform backup keeps milliseconds only)."""
    return sorted(re.sub(r"(\.\d{3})\d{3}", r"\1", json.dumps(r, sort_keys=True, default=str))
                  for r in institute.export_rows(tenant, include_secrets=True))


def setup_three(make_tenant, make_user):
    demo = seed_demo(today=TODAY)
    GatewayAccount.objects.create(tenant=demo, provider="jazzcash", merchant_id="MC1", password="pw", secret="salt", is_enabled=True)
    MessagingSettings.objects.update_or_create(tenant=demo, defaults={"twilio_auth_token": "tok-123"})
    others = []
    for slug in ("beta", "gamma"):
        t = make_tenant(slug)
        make_user("admin", Role.ADMIN, t)  # same username as the demo admin
        for i in range(3):
            Student.objects.create(tenant=t, admission_no=str(i), first_name=f"{slug}{i}", gender="male")
        others.append(t)
    return demo, others


def upload(content, name="backup.json.gz"):
    return SimpleUploadedFile(name, content, content_type="application/gzip")


def test_restore_one_institute_leaves_the_others_untouched(api, super_admin, make_tenant, make_user):
    demo, others = setup_three(make_tenant, make_user)
    before = {t.slug: rows_of(t) for t in [demo, *others]}
    file = institute.export_file(demo, include_secrets=False)  # what the school downloads
    assert b"tok-123" not in gzip.decompress(file) and b'"salt"' not in gzip.decompress(file)

    # The demo school's data goes wrong: students deleted, a bill changed, a new student added.
    Student.objects.filter(tenant=demo, admission_no__in=["1", "2"]).update(status="left")
    inv = Invoice.objects.filter(tenant=demo).first()
    Invoice.objects.filter(pk=inv.pk).update(notes="wrong")
    Student.objects.create(tenant=demo, admission_no="X-99", first_name="Late", gender="male")
    Payment.objects.filter(tenant=demo).first().delete()

    api.force_authenticate(super_admin)
    url = f"/api/platform/tenants/{demo.pk}/restore/"
    preview = api.post(url, {"file": upload(file)}, format="multipart").json()
    assert preview["restored"] is False and preview["source"] == "institute"
    assert preview["backup"]["Students"] == 32 and preview["current"]["Students"] == 33
    assert "confirm_code" in api.post(url, {"file": upload(file), "confirm_code": "beta"}, format="multipart").json()

    res = api.post(url, {"file": upload(file), "confirm_code": "DEMO"}, format="multipart").json()
    assert res["restored"] is True and res["current"]["Students"] == 32
    assert rows_of(demo) == before["demo"]  # exactly as at backup time, secrets kept from before
    for t in others:
        assert rows_of(t) == before[t.slug]  # untouched
    assert GatewayAccount.objects.get(tenant=demo).secret == "salt"
    assert MessagingSettings.objects.get(tenant=demo).twilio_auth_token == "tok-123"
    assert User.objects.get(tenant=demo, username="admin").check_password("demo1234")
    assert not Student.objects.filter(tenant=demo, admission_no="X-99").exists()
    # New rows after the restore still get fresh ids.
    s = Student.objects.create(tenant=demo, admission_no="NEW", first_name="New", gender="male")
    assert s.pk > max(Student.objects.exclude(pk=s.pk).values_list("pk", flat=True))

    # The data from just before the restore was saved and can be put back (undo).
    snap = InstituteSnapshot.objects.get(tenant=demo)
    assert snap.reason == "before restore"
    listed = api.get(f"/api/platform/tenants/{demo.pk}/snapshots/").json()
    assert listed[0]["id"] == snap.pk
    undo = api.post(f"/api/platform/tenants/{demo.pk}/snapshots/{snap.pk}/", {"confirm_code": "demo"}, format="json").json()
    assert undo["restored"] is True
    assert Student.objects.filter(tenant=demo, admission_no="X-99").exists()
    for t in others:
        assert rows_of(t) == before[t.slug]


def test_restore_one_institute_from_the_full_backup(api, super_admin, make_tenant, make_user, tmp_path):
    demo, others = setup_three(make_tenant, make_user)
    beta = others[0]
    before = {t.slug: rows_of(t) for t in [demo, *others]}
    path = create_backup(str(tmp_path))
    Student.objects.filter(tenant=beta).delete()
    Student.objects.filter(tenant=demo, admission_no="1").update(first_name="Changed after backup")

    api.force_authenticate(super_admin)
    with open(path, "rb") as fh:
        content = fh.read()
    preview = api.post(f"/api/platform/tenants/{beta.pk}/restore/", {"file": upload(content)}, format="multipart").json()
    assert preview["source"] == "full" and preview["backup"]["Students"] == 3 and "Students" not in preview["current"]
    api.post(f"/api/platform/tenants/{beta.pk}/restore/", {"file": upload(content), "confirm_code": "beta"}, format="multipart")
    assert rows_of(beta) == before["beta"]
    # The demo school's later change is kept: only beta went back in time.
    assert Student.objects.get(tenant=demo, admission_no="1").first_name == "Changed after backup"
    assert rows_of(others[1]) == before["gamma"]


def test_wrong_files_are_refused(api, super_admin, make_tenant):
    alpha, beta = make_tenant("alpha"), make_tenant("beta")
    api.force_authenticate(super_admin)
    url = f"/api/platform/tenants/{alpha.pk}/restore/"
    other = institute.export_file(beta, include_secrets=False)
    assert "for institute “beta”" in str(api.post(url, {"file": upload(other)}, format="multipart").json())
    assert "not a SchoolMS backup" in str(api.post(url, {"file": upload(b"hello")}, format="multipart").json())
    assert "Choose a backup file" in str(api.post(url, {}, format="multipart").json())


def test_school_downloads_its_own_backup_and_excel(api, admin_a, admin_b, school_a, super_admin):
    Student.objects.create(tenant=school_a, admission_no="7", first_name="Zara", gender="female")
    api.force_authenticate(admin_a)
    assert api.get("/api/institute/backup/status/").json()["last_file"] is None
    res = api.get("/api/institute/backup/")
    assert res.status_code == 200 and res["Content-Disposition"].startswith('attachment; filename="alpha-backup-')
    payload = json.loads(gzip.decompress(res.content))
    assert payload["institute"] == "alpha" and payload["with_secrets"] is False
    assert {r["fields"].get("first_name") for r in payload["rows"] if r["model"] == "students.student"} == {"Zara"}
    assert not any(r["model"] in ("subscriptions.subscription", "agreements.signedagreement") for r in payload["rows"])
    status = api.get("/api/institute/backup/status/").json()
    assert status["days_since_file"] == 0

    xlsx = api.get("/api/institute/backup/excel/")
    wb = load_workbook(io.BytesIO(xlsx.content))
    assert wb.sheetnames == ["Students", "Bills", "Payments", "Results", "Attendance (this session)", "Staff"]
    assert wb["Students"]["B5"].value == "Zara"

    # Other institutes' admins see only their own; school admins cannot use the owner's restore.
    api.force_authenticate(admin_b)
    other = json.loads(gzip.decompress(api.get("/api/institute/backup/").content))
    assert other["institute"] == "beta"
    assert api.get(f"/api/platform/tenants/{school_a.pk}/backup/").status_code == 403
    assert api.post(f"/api/platform/tenants/{school_a.pk}/restore/", {}, format="multipart").status_code == 403

    # The owner's copy keeps the payment keys (for a complete restore).
    GatewayAccount.objects.create(tenant=school_a, provider="easypaisa", merchant_id="1", secret="0123456789abcdef")
    api.force_authenticate(super_admin)
    owner = json.loads(gzip.decompress(api.get(f"/api/platform/tenants/{school_a.pk}/backup/").content))
    assert owner["with_secrets"] is True and "0123456789abcdef" in json.dumps(owner)


def test_expired_school_can_still_download(api, admin_a, school_a):
    from django.utils import timezone

    sub = school_a.subscription
    sub.current_period_end = timezone.now() - datetime.timedelta(days=3)
    sub.save()
    api.force_authenticate(admin_a)
    assert api.get("/api/institute/backup/").status_code == 200
    assert Tenant.objects.count() == 1

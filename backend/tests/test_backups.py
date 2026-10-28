import datetime
import gzip
import json

from apps.accounts.models import Role, User
from apps.backups.models import BackupRecord
from apps.backups.services import backup_summary, create_backup, restore_backup
from apps.fees.models import Invoice, Payment
from apps.students.models import Student
from apps.tenants.demo import seed_demo, wipe_institutes
from apps.tenants.models import Tenant

TODAY = datetime.date(2026, 10, 14)


def snapshot():
    return {
        "tenants": sorted(Tenant.objects.values_list("slug", "name", "logo")),
        "users": sorted(User.objects.values_list("tenant__slug", "username", "password", "role")),
        "students": Student.objects.count(),
        "invoices": sorted(Invoice.objects.values_list("tenant__slug", "number", "total", "paid", "status")),
        "payments": Payment.objects.count(),
    }


def test_backup_and_restore_round_trip(db, make_tenant, make_user, tmp_path):
    seed_demo(today=TODAY)
    other = make_tenant("other")
    # Same username in two institutes: the restore must keep each with its own institute.
    make_user("admin", Role.ADMIN, other)
    before = snapshot()
    path = create_backup(str(tmp_path))
    counts = backup_summary(path)
    assert counts["tenants.tenant"] == 2 and counts["students.student"] == 32
    with gzip.open(path, "rt") as fh:
        assert not any(r["model"].startswith(("contenttypes.", "sessions.")) for r in json.load(fh))

    try:
        restore_backup(path)
        raise AssertionError("restore into a database with institutes must be refused")
    except ValueError:
        pass

    wipe_institutes()
    assert Tenant.objects.count() == 0
    restore_backup(path)
    assert snapshot() == before
    # New rows still get fresh ids after the restore (sequences were moved on).
    demo = Tenant.objects.get(slug="demo")
    s = Student.objects.create(tenant=demo, admission_no="NEW-1", first_name="New", gender="male")
    assert s.pk > max(Student.objects.exclude(pk=s.pk).values_list("pk", flat=True))
    assert User.objects.get(tenant=other, username="admin").role == Role.ADMIN


def test_backup_download_is_for_the_platform_owner(api, super_admin, admin_a):
    api.force_authenticate(admin_a)
    assert api.get("/api/platform/backup/").status_code == 403
    api.force_authenticate(super_admin)
    assert api.get("/api/platform/overview/").json()["last_backup"] is None
    res = api.get("/api/platform/backup/")
    assert res.status_code == 200
    assert res["Content-Disposition"].startswith('attachment; filename="schoolms-backup-')
    rows = json.loads(gzip.decompress(b"".join(res.streaming_content)))
    assert any(r["model"] == "tenants.tenant" and r["fields"]["slug"] == "alpha" for r in rows)
    record = BackupRecord.objects.get()
    assert record.institutes == 1 and record.size_bytes > 0 and record.created_by == super_admin
    assert api.get("/api/platform/overview/").json()["last_backup"]["days_ago"] == 0

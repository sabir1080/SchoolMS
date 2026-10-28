"""Backups of one institute's data, and restoring only that institute (other institutes are never touched).

An institute's data is every row with its ``tenant``, plus rows that belong to those (invoice items, a student's
guardian links, the exams in an annual result), plus the institute's own settings row. Billing (subscription,
payments to the platform, agreements) and device registrations stay as they are: a restore never changes them.
"""

import datetime
import gzip
import json
from functools import lru_cache

from django.apps import apps
from django.core import serializers
from django.core.serializers.json import DjangoJSONEncoder
from django.db import IntegrityError, connection, transaction
from django.db import models
from django.db.models import ProtectedError
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac

FORMAT = "schoolms-institute-backup"
FORMAT_VERSION = 1
# Never part of an institute backup and never changed by a restore.
KEEP_OUT = {
    "subscriptions.subscription", "subscriptions.subscriptionpayment", "agreements.signedagreement",
    "messaging.pushsubscription", "backups.institutebackuplog", "backups.institutesnapshot", "backups.backuprecord",
    "recyclebin.deleteditem",
}
# Secret fields left out of the copy an institute downloads itself (a lost file must not expose payment keys).
SECRETS = {"payments.gatewayaccount": ("password", "secret"), "messaging.messagingsettings": ("twilio_auth_token",)}


class _Encoder(DjangoJSONEncoder):
    """Keeps full microseconds (Django's encoder cuts them to milliseconds), so a restore is exact."""

    def default(self, o):
        if isinstance(o, datetime.datetime):
            return o.isoformat()
        return super().default(o)


def _label(model):
    return model._meta.label_lower


@lru_cache
def owned_models():
    """(direct, children): models with a ``tenant`` field, and models that belong to one of those."""
    from apps.tenants.models import Tenant

    direct = [m for m in apps.get_models() if _label(m) not in KEEP_OUT
              and any(f.name == "tenant" and getattr(f, "related_model", None) is Tenant for f in m._meta.fields)]
    owned = set(direct)
    children = {}
    for m in apps.get_models():
        if m in owned or m is Tenant or _label(m) in KEEP_OUT or m._meta.app_label == "admin":
            continue
        links = [f.name for f in m._meta.fields
                 if f.many_to_one and f.related_model in owned and f.remote_field.on_delete.__name__ == "CASCADE"]
        if links:
            children[m] = links
    return tuple(direct), tuple(children.items())


def export_rows(tenant, include_secrets):
    """The institute's rows as plain Python data (Django's serialization format)."""
    direct, children = owned_models()
    rows = serializers.serialize("python", [tenant])
    for model in direct:
        rows += serializers.serialize("python", model.objects.filter(tenant=tenant).order_by("pk"))
    for model, links in children:
        query = model.objects.none()
        for link in links:
            parent = model._meta.get_field(link).related_model
            query = query | model.objects.filter(**{f"{link}__in": parent.objects.filter(tenant=tenant)})
        rows += serializers.serialize("python", query.distinct().order_by("pk"))
    if not include_secrets:
        for row in rows:
            for field in SECRETS.get(row["model"], ()):
                row["fields"][field] = ""
    return rows


def _signature(content, tenant_pk):
    """Server signature of a backup file, so an institute admin can only restore a file SchoolMS made, unchanged."""
    signed = {k: content.get(k) for k in ("format", "version", "institute", "created_at", "with_secrets", "rows")}
    text = json.dumps(signed, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return salted_hmac("schoolms.institute-backup", f"{tenant_pk}:{text}", algorithm="sha256").hexdigest()


def export_file(tenant, include_secrets):
    """A gzip'd JSON backup of one institute."""
    payload = {
        "format": FORMAT, "version": FORMAT_VERSION, "institute": tenant.slug, "name": tenant.name,
        "created_at": timezone.now().isoformat(), "with_secrets": include_secrets,
        "rows": export_rows(tenant, include_secrets),
    }
    payload = json.loads(json.dumps(payload, cls=_Encoder))  # plain JSON values, exactly as read back
    payload["signature"] = _signature(payload, tenant.pk)
    return gzip.compress(json.dumps(payload).encode())


def without_secrets(data, tenant):
    """A saved copy as the institute may download it: payment keys and tokens blanked, signed again."""
    content = json.loads(gzip.decompress(data))
    for row in content["rows"]:
        for field in SECRETS.get(row["model"], ()):
            if field in row["fields"]:
                row["fields"][field] = ""
    content["with_secrets"] = False
    content["signature"] = _signature(content, tenant.pk)
    return gzip.compress(json.dumps(content).encode())


class BackupFileError(ValueError):
    pass


def read_file(data, tenant):
    """Rows for ``tenant`` from an institute backup or from a full platform backup, plus a description of the file."""
    try:
        content = json.loads(gzip.decompress(data) if data[:2] == b"\x1f\x8b" else data)
    except (OSError, ValueError, EOFError):
        raise BackupFileError("This is not a SchoolMS backup file.")
    if isinstance(content, dict) and content.get("format") == FORMAT:
        if content.get("institute") != tenant.slug:
            raise BackupFileError(f"This backup is for institute “{content.get('institute')}”, not “{tenant.slug}”.")
        signed = constant_time_compare(str(content.get("signature", "")), _signature(content, tenant.pk))
        return content["rows"], {"source": "institute", "created_at": content.get("created_at"),
                                 "with_secrets": content.get("with_secrets"), "signed": signed}
    if isinstance(content, list):
        return extract_from_full(content, tenant), {"source": "full", "created_at": None, "with_secrets": True, "signed": False}
    raise BackupFileError("This is not a SchoolMS backup file.")


def extract_from_full(rows, tenant):
    """Only this institute's rows from a full platform backup."""
    match = [r for r in rows if r["model"] == "tenants.tenant" and r["fields"].get("slug") == tenant.slug]
    if not match:
        raise BackupFileError(f"Institute “{tenant.slug}” is not in this backup.")
    tenant_pk = match[0]["pk"]
    if tenant_pk != tenant.pk:
        raise BackupFileError("This backup comes from another installation of SchoolMS.")
    direct, children = owned_models()
    direct_labels = {_label(m) for m in direct}
    picked = [match[0]] + [r for r in rows if r["model"] in direct_labels and r["fields"].get("tenant") == tenant_pk]
    owned_pks = {}
    for r in picked:
        owned_pks.setdefault(r["model"], set()).add(r["pk"])
    for model, links in children:
        targets = [(link, _label(model._meta.get_field(link).related_model)) for link in links]
        picked += [r for r in rows if r["model"] == _label(model)
                   and any(r["fields"].get(link) in owned_pks.get(parent, ()) for link, parent in targets)]
    return picked


def summary(rows):
    """Rows per model, with readable names (e.g. {"Students": 32})."""
    counts = {}
    for r in rows:
        if r["model"] == "tenants.tenant":
            continue
        name = str(apps.get_model(r["model"])._meta.verbose_name_plural).capitalize()
        counts[name] = counts.get(name, 0) + 1
    return dict(sorted(counts.items()))


def current_summary(tenant):
    return summary(export_rows(tenant, include_secrets=False))


def _delete_institute_rows(tenant):
    direct, _ = owned_models()
    remaining = [m for m in direct if _label(m) != "accounts.user"] + [m for m in direct if _label(m) == "accounts.user"]
    while remaining:
        left = []
        for model in remaining:
            try:
                with transaction.atomic():
                    model.objects.filter(tenant=tenant).delete()
            except ProtectedError:
                left.append(model)
        if len(left) == len(remaining):
            raise RuntimeError(f"Could not clear: {[m.__name__ for m in left]}")
        remaining = left


def snapshot(tenant, reason, user=None):
    from .models import InstituteSnapshot

    data = export_file(tenant, include_secrets=True)
    snap = InstituteSnapshot.objects.create(tenant=tenant, reason=reason, data=data, size_bytes=len(data), created_by=user)
    for old in InstituteSnapshot.objects.filter(tenant=tenant, kind=InstituteSnapshot.RESTORE).order_by("-created_at")[5:]:
        old.delete()
    return snap


def _user_links(tenant):
    """Rows kept out of backups that point at this institute's users (push devices, agreement signers, who deleted
    or backed up what). Restoring deletes and re-creates the users, so these are saved and put back afterwards."""
    from apps.accounts.models import User

    users = User.objects.filter(tenant=tenant)
    links, cascaded = [], []
    for label in sorted(KEEP_OUT):
        model = apps.get_model(label)
        for field in model._meta.concrete_fields:
            if not (field.many_to_one and field.related_model is User):
                continue
            found = model.objects.filter(**{f"{field.name}__in": users})
            if field.remote_field.on_delete is models.CASCADE:
                cascaded += serializers.serialize("python", found)
            else:
                links += [(model, pk, field.attname, uid) for pk, uid in found.values_list("pk", field.attname)]
    return links, cascaded


def _put_back_user_links(links, cascaded):
    from apps.accounts.models import User

    wanted = {uid for *_, uid in links} | {r["fields"][f] for r in cascaded for f in r["fields"] if f == "user"}
    alive = set(User.objects.filter(pk__in=wanted).values_list("pk", flat=True))
    for model, pk, attname, uid in links:
        if uid in alive:
            model.objects.filter(pk=pk).update(**{attname: uid})
    for obj in serializers.deserialize("python", cascaded):
        if obj.object.user_id in alive:
            obj.save()


def backup_has_user(rows, user):
    return any(r["model"] == "accounts.user" and r["pk"] == user.pk for r in rows)


@transaction.atomic
def restore(tenant, rows, user=None, reason="before restore"):
    """Replace this institute's data with ``rows``. Saves the current data first (see ``snapshot``)."""
    from apps.messaging.models import MessagingSettings
    from apps.payments.models import GatewayAccount

    safety = snapshot(tenant, reason, user)
    keys = {a.provider: (a.password, a.secret) for a in GatewayAccount.objects.filter(tenant=tenant)}
    token = MessagingSettings.objects.filter(tenant=tenant).values_list("twilio_auth_token", flat=True).first()
    links, cascaded = _user_links(tenant)

    _delete_institute_rows(tenant)
    tenant_row = next(r for r in rows if r["model"] == "tenants.tenant")
    for field, value in tenant_row["fields"].items():
        if field not in ("slug", "is_active", "created_at"):
            setattr(tenant, field, value)
    tenant.save()
    objects = list(serializers.deserialize("python", [r for r in rows if r["model"] != "tenants.tenant"]))
    tables = {obj.object._meta.db_table for obj in objects}
    try:
        with connection.constraint_checks_disabled():
            for obj in objects:
                obj.save()
        connection.check_constraints(table_names=sorted(tables))
    except IntegrityError as exc:
        raise BackupFileError(f"The backup could not be restored: {exc}")

    for account in GatewayAccount.objects.filter(tenant=tenant):
        old = keys.get(account.provider)
        if old and not account.secret:
            account.password, account.secret = old
            account.save(update_fields=["password", "secret"])
    if token:
        MessagingSettings.objects.filter(tenant=tenant, twilio_auth_token="").update(twilio_auth_token=token)
    _put_back_user_links(links, cascaded)
    return safety, summary(rows)

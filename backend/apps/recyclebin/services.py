"""Recycle bin: deleting through the app keeps a copy for 30 days, so an admin can bring it back.

``trash`` deletes exactly what a normal delete would (same protections), after saving every row that goes with it
(e.g. a student's enrollments, guardian links and login) and every link that the delete clears.
"""

import datetime

from django.core import serializers
from django.db import IntegrityError, connection, router, transaction
from django.db.models.deletion import Collector
from django.utils import timezone

from .models import KEEP_DAYS, DeletedItem


class RestoreConflict(Exception):
    pass


def describe(obj):
    """A short, readable name for what was deleted."""
    label = obj._meta.label_lower
    if label == "fees.payment":
        return f"Payment: receipt {obj.receipt_number} · {obj.invoice.student.full_name} · {obj.invoice.tenant.currency} {obj.amount:,.0f}"
    if label == "homework.homework":
        return f"Homework: {obj.title} ({obj.section}, {obj.date:%d %b %Y})"
    if label == "payroll.payslip":
        return f"Salary slip: {obj.employee.name} · {obj.period}"
    if label == "certificates.certificate":
        return f"Certificate: {obj.get_kind_display()} · {obj.student.full_name}"
    if label == "admissions.application":
        return f"Admission application: {obj.full_name}"
    if label == "students.student":
        return f"Student: {obj.full_name} (Adm {obj.admission_no})"
    if label == "timetable.timetableentry":
        return f"Timetable period: {obj.section} · {obj.get_day_display() if hasattr(obj, 'get_day_display') else obj.day}"
    return f"{str(obj._meta.verbose_name).capitalize()}: {obj}"


def purge_old(tenant):
    DeletedItem.objects.filter(tenant=tenant, created_at__lt=timezone.now() - datetime.timedelta(days=KEEP_DAYS)).delete()


@transaction.atomic
def trash(objs, user=None, kind=None, label=None):
    """Delete ``objs`` (one object or several, first one names the item) and keep a copy in the recycle bin."""
    objs = objs if isinstance(objs, (list, tuple)) else [objs]
    objs = [o for o in objs if o is not None]
    first = objs[0]
    tenant = first.tenant
    item_label = label or describe(first)
    collector = Collector(using=router.db_for_write(type(first)))
    for obj in objs:
        collector.collect([obj])
    rows = []
    for model, instances in collector.data.items():
        rows += serializers.serialize("python", sorted(instances, key=lambda o: o.pk))
    for qs in collector.fast_deletes:
        rows += serializers.serialize("python", qs.order_by("pk"))
    relinks = []
    for (field, _value), targets in collector.field_updates.items():
        for target in targets:
            queryset = target if hasattr(target, "values_list") else type(target).objects.filter(pk=target.pk)
            for pk, linked in queryset.values_list("pk", field.attname):
                relinks.append({"model": field.model._meta.label_lower, "field": field.attname, "pk": pk, "value": linked})
    collector.delete()
    return DeletedItem.objects.create(
        tenant=tenant, kind=kind or first._meta.model_name, label=item_label[:255], rows=_jsonable(rows),
        relinks=relinks, deleted_by=user,
    )


def _jsonable(rows):
    """Rows with dates/decimals as text (JSONField storage)."""
    import json

    from django.core.serializers.json import DjangoJSONEncoder

    return json.loads(json.dumps(rows, cls=DjangoJSONEncoder))


@transaction.atomic
def restore(item, user=None):
    """Put the deleted rows back (same ids), re-link what the delete cleared, and fix totals that depend on them."""
    from django.apps import apps

    if item.restored_at:
        raise RestoreConflict("This item was already restored.")
    objects = list(serializers.deserialize("python", item.rows))
    tables = {o.object._meta.db_table for o in objects}
    try:
        with transaction.atomic():
            with connection.constraint_checks_disabled():
                for obj in objects:
                    obj.save()
            for link in item.relinks:
                model = apps.get_model(link["model"])
                model.objects.filter(pk=link["pk"], **{link["field"]: None}).update(**{link["field"]: link["value"]})
            connection.check_constraints(table_names=sorted(tables))
    except IntegrityError:
        raise RestoreConflict(
            "This cannot be restored because something with the same number or name was added after it was deleted "
            "(for example the same admission number, roll number or receipt). Change that first, then try again."
        )
    _after_restore(objects)
    item.restored_at = timezone.now()
    item.save(update_fields=["restored_at", "updated_at"])
    return item


def _after_restore(objects):
    from apps.fees.models import Payment

    for obj in objects:
        if isinstance(obj.object, Payment):
            obj.object.invoice.refresh_totals()

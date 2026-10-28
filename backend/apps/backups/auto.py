"""Daily automatic backups.

The free server sleeps when nobody uses it, so there is no clock to run a nightly job. Instead, the first signed-in
use of an institute each day (in its own timezone) saves a copy of its data in the background, like the admin's
Download backup. Data only changes while someone uses the app, so a day without use needs no new copy.
"""

import datetime
import logging
import threading
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import IntegrityError, connection, transaction

from apps.core.timeutils import tenant_today

KEEP_DAYS = 14
logger = logging.getLogger(__name__)

_done = {}  # tenant id -> (day backed up, timezone name), so most requests cost nothing
_running = set()
_lock = threading.Lock()


def forget(tenant_id):
    """Check again on the next request (e.g. automatic backup was just switched on)."""
    _done.pop(tenant_id, None)


def _today_known(tenant_id):
    known = _done.get(tenant_id)
    if not known:
        return False
    try:
        return datetime.datetime.now(ZoneInfo(known[1])).date() == known[0]
    except (ValueError, KeyError):
        return False


def schedule(tenant_id):
    """Make today's backup for this institute unless it exists (called after each signed-in request)."""
    if _today_known(tenant_id):
        return
    with _lock:
        if tenant_id in _running:
            return
        _running.add(tenant_id)
    if getattr(settings, "AUTO_BACKUP_ASYNC", True):
        threading.Thread(target=_run_in_thread, args=(tenant_id,), daemon=True).start()
    else:
        _run(tenant_id)


def _run_in_thread(tenant_id):
    try:
        _run(tenant_id)
    finally:
        connection.close()  # this thread's own database connection


def _run(tenant_id):
    from apps.tenants.models import Tenant

    from . import institute
    from .models import InstituteSnapshot

    try:
        tenant = Tenant.objects.filter(pk=tenant_id).first()
        if tenant is None:
            return
        day = tenant_today(tenant)
        auto = InstituteSnapshot.objects.filter(tenant=tenant, kind=InstituteSnapshot.AUTO)
        if tenant.auto_backup and not auto.filter(day=day).exists():
            data = institute.export_file(tenant, include_secrets=True)
            try:
                with transaction.atomic():
                    InstituteSnapshot.objects.create(tenant=tenant, kind=InstituteSnapshot.AUTO, day=day,
                                                     reason="daily automatic backup", data=data, size_bytes=len(data))
            except IntegrityError:
                pass  # another worker made it at the same moment
            auto.filter(day__lte=day - datetime.timedelta(days=KEEP_DAYS)).delete()
        _done[tenant_id] = (day, tenant.timezone or settings.TIME_ZONE)
    except Exception:
        logger.exception("Daily backup failed for institute %s", tenant_id)
    finally:
        with _lock:
            _running.discard(tenant_id)


class AutoBackupMiddleware:
    """After a signed-in institute user's request, make sure the institute has today's backup."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        user = getattr(request, "user", None)  # DRF puts the token's user here once a view authenticated it
        tenant_id = getattr(user, "tenant_id", None) if user is not None and user.is_authenticated else None
        if tenant_id and getattr(settings, "AUTO_BACKUP", True) and response.status_code < 500:
            schedule(tenant_id)
        return response

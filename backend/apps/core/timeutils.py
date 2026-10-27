import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.utils import timezone
from rest_framework import serializers


def tenant_today(tenant):
    """Today's date in the institute's own timezone (the server runs on UTC)."""
    try:
        zone = ZoneInfo(tenant.timezone) if tenant and tenant.timezone else None
    except (ZoneInfoNotFoundError, ValueError):
        zone = None
    return timezone.localdate(timezone=zone) if zone else timezone.localdate()


def parse_month(value, today):
    """'2026-10' -> (first day, last day); defaults to the month of ``today``."""
    try:
        first = datetime.date.fromisoformat(f"{value}-01") if value else today.replace(day=1)
    except ValueError:
        raise serializers.ValidationError({"month": ["Use the format YYYY-MM."]})
    next_month = (first.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
    return first, next_month - datetime.timedelta(days=1)

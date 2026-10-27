from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.utils import timezone


def tenant_today(tenant):
    """Today's date in the institute's own timezone (the server runs on UTC)."""
    try:
        zone = ZoneInfo(tenant.timezone) if tenant and tenant.timezone else None
    except (ZoneInfoNotFoundError, ValueError):
        zone = None
    return timezone.localdate(timezone=zone) if zone else timezone.localdate()

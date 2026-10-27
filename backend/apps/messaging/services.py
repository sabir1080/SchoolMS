"""Queueing and sending parent alerts (absent, fee, result, homework, notices).

With the free "WhatsApp link" channel messages wait in the outbox and the admin sends each one from
their phone (wa.me link). With Twilio they are sent right away; failures stay in the outbox to retry.
Nothing is sent unless the institute's plan includes alerts.
"""

import base64
import json
import re
import urllib.error
import urllib.parse
import urllib.request

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.students.models import StudentGuardian
from apps.subscriptions.features import Feature

from . import push
from .models import AUTOMATIC, Channel, Message, MessagingSettings, Status

SEND_NOW_LIMIT = 50  # automatic sends per request; the rest wait for "Send pending"


def settings_for(tenant):
    obj, _ = MessagingSettings.objects.get_or_create(tenant=tenant)
    return obj


def alerts_enabled(tenant):
    subscription = getattr(tenant, "subscription", None)
    return bool(subscription and subscription.is_usable and Feature.SMS_ALERTS in subscription.plan.features)


def normalize_phone(raw, country="PK"):
    """'0300-1234567' -> '+923001234567'. Returns '' when it does not look like a phone number."""
    raw = (raw or "").strip()
    digits = re.sub(r"\D", "", raw)
    if raw.startswith("+"):
        return f"+{digits}" if 8 <= len(digits) <= 15 else ""
    if digits.startswith("00"):
        digits = digits[2:]
        return f"+{digits}" if 8 <= len(digits) <= 15 else ""
    if country == "PK":
        if digits.startswith("0") and len(digits) == 11:
            return f"+92{digits[1:]}"
        if digits.startswith("92") and len(digits) == 12:
            return f"+{digits}"
        if digits.startswith("3") and len(digits) == 10:
            return f"+92{digits}"
    return ""


def contact_for(student):
    """(name, phone) of the student's primary guardian, falling back to the student's own phone."""
    link = StudentGuardian.objects.filter(student=student).select_related("guardian").order_by("-is_primary", "id").first()
    if link and link.guardian.phone:
        return link.guardian.name, link.guardian.phone
    return student.full_name, student.phone


def queue(tenant, student, kind, body, key="", user=None):
    """Create a message for the student's parent (once per ``key``). Returns it, or None if it already exists."""
    name, raw_phone = contact_for(student) if student else ("", "")
    phone = normalize_phone(raw_phone, tenant.country)
    cfg = settings_for(tenant)
    try:
        with transaction.atomic():
            return Message.objects.create(
                tenant=tenant, student=student, recipient=name, phone=phone, body=body, kind=kind,
                channel=cfg.channel, dedupe_key=key, created_by=user,
                status=Status.PENDING if phone else Status.FAILED, error="" if phone else "No valid phone number",
            )
    except IntegrityError:
        return None


def twilio_send(cfg, phone, body):
    """Send one message through Twilio's REST API. Returns (ok, error)."""
    whatsapp = cfg.channel == Channel.TWILIO_WHATSAPP
    data = urllib.parse.urlencode({
        "To": f"whatsapp:{phone}" if whatsapp else phone,
        "From": f"whatsapp:{cfg.twilio_from}" if whatsapp else cfg.twilio_from,
        "Body": body,
    }).encode()
    request = urllib.request.Request(
        f"https://api.twilio.com/2010-04-01/Accounts/{cfg.twilio_account_sid}/Messages.json", data=data, method="POST"
    )
    token = base64.b64encode(f"{cfg.twilio_account_sid}:{cfg.twilio_auth_token}".encode()).decode()
    request.add_header("Authorization", f"Basic {token}")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return 200 <= response.status < 300, ""
    except urllib.error.HTTPError as err:
        try:
            detail = json.loads(err.read().decode()).get("message", "")
        except ValueError:
            detail = ""
        return False, f"Twilio {err.code}: {detail}"[:250]
    except (urllib.error.URLError, TimeoutError, OSError):
        return False, "Could not reach Twilio. Please try again later."


def send(messages, cfg):
    """Send pending messages automatically when the institute uses Twilio. Returns (sent, failed)."""
    if not cfg.is_automatic:
        return 0, 0
    sent = failed = 0
    for message in messages[:SEND_NOW_LIMIT]:
        if message.status == Status.SENT or not message.phone:
            continue
        ok, error = twilio_send(cfg, message.phone, message.body)
        message.status, message.error, message.channel = (Status.SENT if ok else Status.FAILED), ("" if ok else error), cfg.channel
        message.sent_at = timezone.now() if ok else None
        message.save(update_fields=["status", "error", "channel", "sent_at", "updated_at"])
        sent, failed = sent + ok, failed + (not ok)
    return sent, failed


def queue_and_send(tenant, items, kind, user=None):
    """``items`` is a list of (student, body, key). Queues each once and sends them if automatic."""
    if not alerts_enabled(tenant):
        return []
    created = [m for m in (queue(tenant, s, kind, body, key, user) for s, body, key in items) if m]
    push.notify_for_messages(created)
    cfg = settings_for(tenant)
    if cfg.channel in AUTOMATIC:
        send([m for m in created if m.status == Status.PENDING], cfg)
    return created


def whatsapp_link(message):
    return f"https://wa.me/{message.phone.lstrip('+')}?text={urllib.parse.quote(message.body)}"

"""Web Push notifications (RFC 8030/8291/8292) to phones and browsers where a user turned them on.

Parents and students get the same alerts they receive by SMS/WhatsApp as a free phone notification.
Needs VAPID keys in the environment (``python manage.py generate_vapid_keys``); without them push is off.
"""

import base64
import json
import logging
import os
import struct
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from cryptography.hazmat.primitives import hashes, hmac, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings
from django.db import transaction

logger = logging.getLogger(__name__)

# Push services of Chrome/Android, Firefox, Edge/Windows and Safari/iOS. Only these get our requests
# (the endpoint comes from the browser, so it must not point the server anywhere else).
PUSH_HOSTS = ("fcm.googleapis.com", "updates.push.services.mozilla.com", "push.services.mozilla.com",
              "web.push.apple.com", "notify.windows.com")
RECORD_SIZE = 4096


def b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def b64url_decode(text):
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def private_key():
    raw = os.environ.get("VAPID_PRIVATE_KEY", "") or getattr(settings, "VAPID_PRIVATE_KEY", "")
    if not raw:
        return None
    return ec.derive_private_key(int.from_bytes(b64url_decode(raw), "big"), ec.SECP256R1())


def public_key_b64():
    key = private_key()
    if key is None:
        return ""
    return b64url(key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint))


def enabled():
    return private_key() is not None


def endpoint_allowed(endpoint):
    parts = urllib.parse.urlsplit(endpoint)
    host = (parts.hostname or "").lower()
    extra = [h.strip() for h in getattr(settings, "PUSH_EXTRA_HOSTS", []) if h.strip()]
    if host in extra:
        return parts.scheme in ("http", "https")
    return parts.scheme == "https" and any(host == h or host.endswith("." + h) for h in PUSH_HOSTS)


def _hmac(key, data):
    h = hmac.HMAC(key, hashes.SHA256())
    h.update(data)
    return h.finalize()


def encrypt(payload, p256dh, auth):
    """aes128gcm content encoding for one push message (RFC 8291)."""
    ua_public = b64url_decode(p256dh)
    auth_secret = b64url_decode(auth)
    server_key = ec.generate_private_key(ec.SECP256R1())
    as_public = server_key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    shared = server_key.exchange(ec.ECDH(), ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), ua_public))
    ikm = _hmac(_hmac(auth_secret, shared), b"WebPush: info\x00" + ua_public + as_public + b"\x01")
    salt = os.urandom(16)
    prk = _hmac(salt, ikm)
    cek = _hmac(prk, b"Content-Encoding: aes128gcm\x00\x01")[:16]
    nonce = _hmac(prk, b"Content-Encoding: nonce\x00\x01")[:12]
    body = AESGCM(cek).encrypt(nonce, payload + b"\x02", None)
    return salt + struct.pack("!IB", RECORD_SIZE, len(as_public)) + as_public + body


def vapid_header(endpoint):
    """``Authorization: vapid t=<JWT>, k=<public key>`` for the push service of ``endpoint`` (RFC 8292)."""
    parts = urllib.parse.urlsplit(endpoint)
    claims = {"aud": f"{parts.scheme}://{parts.netloc}", "exp": int(time.time()) + 12 * 3600,
              "sub": getattr(settings, "VAPID_SUBJECT", "mailto:support@schoolms.app")}
    signing_input = b64url(json.dumps({"typ": "JWT", "alg": "ES256"}).encode()) + "." + b64url(json.dumps(claims).encode())
    r, s = decode_dss_signature(private_key().sign(signing_input.encode(), ec.ECDSA(hashes.SHA256())))
    token = signing_input + "." + b64url(r.to_bytes(32, "big") + s.to_bytes(32, "big"))
    return f"vapid t={token}, k={public_key_b64()}"


def send_one(subscription, data):
    """Send one notification. Returns True when the push service accepted it."""
    from .models import PushSubscription

    if not endpoint_allowed(subscription.endpoint):
        return False
    request = urllib.request.Request(
        subscription.endpoint,
        data=encrypt(json.dumps(data).encode(), subscription.p256dh, subscription.auth),
        method="POST",
        headers={"Content-Encoding": "aes128gcm", "Content-Type": "application/octet-stream", "TTL": "86400",
                 "Urgency": "normal", "Authorization": vapid_header(subscription.endpoint)},
    )
    try:
        with urllib.request.urlopen(request, timeout=8):
            return True
    except urllib.error.HTTPError as err:
        if err.code in (404, 410):  # the user turned notifications off or uninstalled: forget the device
            PushSubscription.objects.filter(pk=subscription.pk).delete()
        else:
            PushSubscription.objects.filter(pk=subscription.pk).update(last_error=f"HTTP {err.code}")
    except (urllib.error.URLError, OSError) as err:
        PushSubscription.objects.filter(pk=subscription.pk).update(last_error=str(err)[:255])
    return False


def send_to_users(users, title, body, url="/dashboard/"):
    """Notify every device of these users (in the background, after the current transaction)."""
    from .models import PushSubscription

    if not enabled():
        return
    ids = [u.pk for u in users if u is not None and u.is_active]
    if not ids:
        return
    data = {"title": title, "body": body[:400], "url": url}

    def run():
        try:
            for sub in PushSubscription.objects.filter(user_id__in=ids):
                send_one(sub, data)
        except Exception:  # noqa: BLE001 - never break the request that queued the alert
            logger.exception("Push notifications failed")

    if getattr(settings, "PUSH_SYNC", False):
        transaction.on_commit(run)
    else:
        transaction.on_commit(lambda: threading.Thread(target=run, daemon=True).start())


def notify_for_messages(messages):
    """A phone notification to the parents (with a login) and the student for each queued alert."""
    from apps.students.models import StudentGuardian

    if not enabled():
        return
    for message in messages:
        student = message.student
        users = [link.guardian.user for link in StudentGuardian.objects.filter(student=student).select_related("guardian__user")]
        users.append(student.user)
        title, _, text = message.body.partition(": ")
        send_to_users(users, title or message.tenant.name, text or message.body)

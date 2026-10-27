import datetime
import json
import struct

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from apps.academics.models import AcademicSession, Program, Section
from apps.accounts.models import Role
from apps.core.timeutils import tenant_today
from apps.messaging import push
from apps.messaging.models import PushSubscription
from apps.students.models import Enrollment, Guardian, Student, StudentGuardian

ENDPOINT = "https://fcm.googleapis.com/fcm/send/abc123"


@pytest.fixture
def vapid(settings):
    key = ec.generate_private_key(ec.SECP256R1())
    settings.VAPID_PRIVATE_KEY = push.b64url(key.private_numbers().private_value.to_bytes(32, "big"))
    settings.PUSH_SYNC = True
    return key


def browser_keys():
    """What a browser creates when subscribing: a P-256 key pair and a 16-byte auth secret."""
    key = ec.generate_private_key(ec.SECP256R1())
    public = key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    return key, push.b64url(public), push.b64url(b"0123456789abcdef")


def decrypt(body, ua_key, ua_public_b64, auth_b64):
    """The browser side of RFC 8291, written out separately to check our encryption."""
    salt, rs, idlen = body[:16], struct.unpack("!I", body[16:20])[0], body[20]
    as_public = body[21:21 + idlen]
    assert rs == 4096 and idlen == 65
    shared = ua_key.exchange(ec.ECDH(), ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), as_public))
    ua_public = push.b64url_decode(ua_public_b64)
    ikm = push._hmac(push._hmac(push.b64url_decode(auth_b64), shared), b"WebPush: info\x00" + ua_public + as_public + b"\x01")
    prk = push._hmac(salt, ikm)
    cek = push._hmac(prk, b"Content-Encoding: aes128gcm\x00\x01")[:16]
    nonce = push._hmac(prk, b"Content-Encoding: nonce\x00\x01")[:12]
    plain = AESGCM(cek).decrypt(nonce, body[21 + idlen:], None)
    assert plain.endswith(b"\x02")
    return plain[:-1]


def test_encryption_round_trip():
    key, public, auth = browser_keys()
    message = json.dumps({"title": "Alpha", "body": "Ali was absent today"}).encode()
    assert decrypt(push.encrypt(message, public, auth), key, public, auth) == message


def test_vapid_header_is_signed_for_the_push_service(vapid):
    header = push.vapid_header(ENDPOINT)
    token = header.split("t=")[1].split(",")[0]
    k = header.split("k=")[1]
    head, claims, sig = token.split(".")
    payload = json.loads(push.b64url_decode(claims))
    assert payload["aud"] == "https://fcm.googleapis.com" and payload["sub"].startswith("mailto:")
    raw = push.b64url_decode(sig)
    public = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), push.b64url_decode(k))
    public.verify(encode_dss_signature(int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:], "big")),
                  f"{head}.{claims}".encode(), ec.ECDSA(hashes.SHA256()))


def test_only_real_push_services_are_contacted(settings):
    assert push.endpoint_allowed(ENDPOINT)
    assert push.endpoint_allowed("https://web.push.apple.com/QGd")
    assert push.endpoint_allowed("https://wns2-par02p.notify.windows.com/w/?token=x")
    for bad in ("http://fcm.googleapis.com/x", "https://evil.example/x", "https://fcm.googleapis.com.evil.example/x",
                "https://169.254.169.254/latest", "https://localhost/x"):
        assert not push.endpoint_allowed(bad), bad


def test_subscribe_test_and_unsubscribe(api, admin_a, vapid, monkeypatch):
    api.force_authenticate(admin_a)
    info = api.get("/api/push/").json()
    assert info["enabled"] is True and len(push.b64url_decode(info["public_key"])) == 65 and info["devices"] == 0
    _, public, auth = browser_keys()
    assert api.post("/api/push/", {"endpoint": "https://evil.example/x", "keys": {"p256dh": public, "auth": auth}}, format="json").status_code == 400
    assert api.post("/api/push/", {"endpoint": ENDPOINT, "keys": {"p256dh": "short", "auth": auth}}, format="json").status_code == 400
    assert api.post("/api/push/", {"endpoint": ENDPOINT, "keys": {"p256dh": public, "auth": auth}}, format="json").json() == {"devices": 1}

    sent = []

    class Reply:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(request, timeout):
        sent.append(request)
        return Reply()

    monkeypatch.setattr(push.urllib.request, "urlopen", fake_urlopen)
    assert api.post("/api/push/", {"action": "test"}, format="json").json() == {"sent": 1, "devices": 1}
    req = sent[0]
    assert req.full_url == ENDPOINT and req.get_header("Content-encoding") == "aes128gcm"
    assert req.get_header("Authorization").startswith("vapid t=")
    assert api.post("/api/push/", {"action": "unsubscribe", "endpoint": ENDPOINT}, format="json").json() == {"devices": 0}


def test_push_disabled_without_keys(api, admin_a, settings):
    settings.VAPID_PRIVATE_KEY = ""
    api.force_authenticate(admin_a)
    assert api.get("/api/push/").json()["enabled"] is False
    _, public, auth = browser_keys()
    assert api.post("/api/push/", {"endpoint": ENDPOINT, "keys": {"p256dh": public, "auth": auth}}, format="json").status_code == 400


def test_absent_alert_reaches_parent_phone_and_gone_devices_are_dropped(api, admin_a, make_user, school_a, vapid, monkeypatch,
                                                                       django_capture_on_commit_callbacks):
    today = tenant_today(school_a)
    session = AcademicSession.objects.create(tenant=school_a, name="S", start_date=today - datetime.timedelta(days=30),
                                             end_date=today + datetime.timedelta(days=200), is_current=True)
    sec = Section.objects.create(tenant=school_a, program=Program.objects.create(tenant=school_a, name="Class 5"), session=session, name="A")
    ali = Student.objects.create(tenant=school_a, admission_no="1", first_name="Ali", gender="male")
    Enrollment.objects.create(tenant=school_a, student=ali, section=sec)
    parent = make_user("raza", Role.PARENT, school_a)
    StudentGuardian.objects.create(student=ali, guardian=Guardian.objects.create(tenant=school_a, name="Raza", phone="03001234567", user=parent), is_primary=True)
    key, public, auth = browser_keys()
    PushSubscription.objects.create(tenant=school_a, user=parent, endpoint=ENDPOINT, p256dh=public, auth=auth)
    PushSubscription.objects.create(tenant=school_a, user=parent, endpoint=ENDPOINT + "-old", p256dh=public, auth=auth)

    bodies = []

    class Reply:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(request, timeout):
        if request.full_url.endswith("-old"):
            raise push.urllib.error.HTTPError(request.full_url, 410, "Gone", {}, None)
        bodies.append(request.data)
        return Reply()

    monkeypatch.setattr(push.urllib.request, "urlopen", fake_urlopen)
    api.force_authenticate(admin_a)
    with django_capture_on_commit_callbacks(execute=True):
        res = api.post("/api/attendance/sheet/", {"section": sec.pk, "date": str(today), "records": [{"student": ali.pk, "status": "absent"}]}, format="json")
    assert res.status_code == 200
    assert len(bodies) == 1
    data = json.loads(decrypt(bodies[0], key, public, auth))
    assert data["title"] == "Alpha" and data["body"].startswith("Ali (Class 5 - A) was absent today") and data["url"] == "/dashboard/"
    assert list(PushSubscription.objects.values_list("endpoint", flat=True)) == [ENDPOINT]

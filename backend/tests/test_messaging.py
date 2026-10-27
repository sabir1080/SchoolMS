import datetime

import pytest

from apps.academics.models import AcademicSession, Program, Section, Subject
from apps.accounts.models import Role
from apps.core.timeutils import tenant_today
from apps.exams.models import ExamSubject, Mark
from apps.fees.services import create_invoice
from apps.messaging import services
from apps.messaging.models import Message
from apps.messaging.services import normalize_phone
from apps.students.models import Enrollment, Guardian, Student, StudentGuardian


def auth(api, user):
    api.force_authenticate(user)
    return api


@pytest.fixture
def ms(school_a):
    today = tenant_today(school_a)
    session = AcademicSession.objects.create(
        tenant=school_a, name="Now", start_date=today - datetime.timedelta(days=100), end_date=today + datetime.timedelta(days=200), is_current=True,
    )
    c5 = Program.objects.create(tenant=school_a, name="Class 5")
    c5.subjects.set([Subject.objects.create(tenant=school_a, name="English")])
    sec = Section.objects.create(tenant=school_a, program=c5, session=session, name="A")
    kids = {}
    for name, phone in (("Ali", "0300-1234567"), ("Sara", "0321 7654321"), ("Bilal", "")):
        kid = Student.objects.create(tenant=school_a, admission_no=name, first_name=name, gender="male")
        Enrollment.objects.create(tenant=school_a, student=kid, section=sec, session=session)
        StudentGuardian.objects.create(student=kid, guardian=Guardian.objects.create(tenant=school_a, name=f"{name}'s father", phone=phone), is_primary=True)
        kids[name] = kid
    return {"today": today, "session": session, "c5": c5, "sec": sec, "kids": kids}


def mark(api, ms, statuses, date=None):
    records = [{"student": ms["kids"][n].pk, "status": s} for n, s in statuses.items()]
    return api.post("/api/attendance/sheet/", {"section": ms["sec"].pk, "date": str(date or ms["today"]), "records": records}, format="json")


def test_normalize_phone():
    assert normalize_phone("0300-1234567") == "+923001234567"
    assert normalize_phone("92 300 1234567") == "+923001234567"
    assert normalize_phone("3001234567") == "+923001234567"
    assert normalize_phone("+44 7700 900123", "PK") == "+447700900123"
    assert normalize_phone("0044 7700 900123") == "+447700900123"
    assert normalize_phone("12345") == "" and normalize_phone("") == ""


def test_absent_alerts_queue_once_and_withdraw(api, admin_a, ms):
    api = auth(api, admin_a)
    assert mark(api, ms, {"Ali": "absent", "Sara": "present", "Bilal": "absent"}).status_code == 200
    messages = {m.student.first_name: m for m in Message.objects.all()}
    assert set(messages) == {"Ali", "Bilal"}
    ali = messages["Ali"]
    assert (ali.phone, ali.status, ali.recipient) == ("+923001234567", "pending", "Ali's father")
    assert "Ali (Class 5 - A) was absent today" in ali.body
    assert (messages["Bilal"].status, messages["Bilal"].error) == ("failed", "No valid phone number")
    mark(api, ms, {"Ali": "absent", "Sara": "present", "Bilal": "absent"})
    assert Message.objects.count() == 2  # no repeat
    mark(api, ms, {"Ali": "present", "Sara": "present", "Bilal": "absent"})
    assert not Message.objects.filter(student=ms["kids"]["Ali"]).exists()  # withdrawn while still pending
    mark(api, ms, {"Ali": "absent"}, date=ms["today"] - datetime.timedelta(days=1))
    assert not Message.objects.filter(student=ms["kids"]["Ali"]).exists()  # past days don't alert
    outbox = api.get("/api/messages/").json()
    assert outbox["summary"] == {"pending": 0, "sent": 0, "failed": 1}


def test_whatsapp_link_and_mark_sent(api, admin_a, ms):
    api = auth(api, admin_a)
    mark(api, ms, {"Ali": "absent"})
    msg = api.get("/api/messages/?status=pending").json()["results"][0]
    assert msg["whatsapp_link"].startswith("https://wa.me/923001234567?text=")
    assert api.post(f"/api/messages/{msg['id']}/mark-sent/").json()["status"] == "sent"
    assert "Automatic sending is not set up" in str(api.post("/api/messages/send-pending/").json())


def test_alert_settings_and_plan(api, admin_a, ms, school_a):
    api = auth(api, admin_a)
    assert api.patch("/api/messages/settings/", {"absent_alerts": False}, format="json").json()["absent_alerts"] is False
    mark(api, ms, {"Ali": "absent"})
    assert Message.objects.count() == 0
    api.patch("/api/messages/settings/", {"absent_alerts": True}, format="json")
    plan = school_a.subscription.plan
    plan.features = [f for f in plan.features if f != "sms_alerts"]
    plan.save()
    mark(api, ms, {"Ali": "absent"})
    assert Message.objects.count() == 0  # plan without alerts: attendance works, nothing is queued
    assert api.get("/api/messages/").status_code == 402


def test_twilio_sending(api, admin_a, ms, monkeypatch):
    sent = []
    monkeypatch.setattr(services, "twilio_send", lambda cfg, phone, body: (sent.append((cfg.channel, phone)) or (phone != "+923217654321", "Twilio 400: bad number")))
    api = auth(api, admin_a)
    assert "Twilio needs" in str(api.patch("/api/messages/settings/", {"channel": "twilio_sms"}, format="json").json())
    res = api.patch("/api/messages/settings/", {"channel": "twilio_sms", "twilio_account_sid": "AC123", "twilio_auth_token": "secret", "twilio_from": "+14155238886"}, format="json").json()
    assert res["has_token"] is True and res["is_automatic"] is True and "twilio_auth_token" not in res
    api.patch("/api/messages/settings/", {"twilio_auth_token": ""}, format="json")  # blank keeps the token
    mark(api, ms, {"Ali": "absent", "Sara": "absent"})
    statuses = {m.student.first_name: (m.status, m.error) for m in Message.objects.all()}
    assert statuses == {"Ali": ("sent", ""), "Sara": ("failed", "Twilio 400: bad number")}
    assert sent == [("twilio_sms", "+923001234567"), ("twilio_sms", "+923217654321")]
    monkeypatch.setattr(services, "twilio_send", lambda cfg, phone, body: (True, ""))
    assert api.post("/api/messages/send-pending/").json() == {"sent": 1, "failed": 0, "left": 0}
    assert Message.objects.filter(status="sent").count() == 2


def test_fee_reminders(api, admin_a, ms, school_a):
    ali = ms["kids"]["Ali"]
    create_invoice(school_a, ali, ms["session"], "September fee", ms["today"] - datetime.timedelta(days=40), ms["today"] - datetime.timedelta(days=30), [{"description": "Tuition", "amount": 4500, "discount": 0}])
    create_invoice(school_a, ali, ms["session"], "October fee", ms["today"], ms["today"] + datetime.timedelta(days=5), [{"description": "Tuition", "amount": 4500, "discount": 0}])
    api = auth(api, admin_a)
    assert api.post("/api/messages/fee-reminders/").json() == {"created": 1}
    body = Message.objects.get().body
    assert "Amount due: PKR 4,500 (September fee)" in body
    assert api.post("/api/messages/fee-reminders/").json() == {"created": 0}  # once a day


def test_result_alerts_when_published(api, admin_a, ms, school_a):
    api = auth(api, admin_a)
    exam = api.post("/api/exams/", {"session": ms["session"].pk, "name": "First Term", "programs": [ms["c5"].pk]}, format="json").json()
    paper = ExamSubject.objects.get(exam_id=exam["id"])
    Mark.objects.create(tenant=school_a, paper=paper, student=ms["kids"]["Ali"], section=ms["sec"], marks_obtained=88)
    Mark.objects.create(tenant=school_a, paper=paper, student=ms["kids"]["Sara"], section=ms["sec"], marks_obtained=20)
    api.patch(f"/api/exams/{exam['id']}/", {"status": "published"}, format="json")
    bodies = {m.student.first_name: m.body for m in Message.objects.filter(kind="result")}
    assert set(bodies) == {"Ali", "Sara"}  # Bilal has no marks (incomplete)
    assert "Ali's First Term result: 88%, grade A, Pass, position 1" in bodies["Ali"]
    assert "Fail" in bodies["Sara"]
    api.patch(f"/api/exams/{exam['id']}/", {"status": "marks_open"}, format="json")
    api.patch(f"/api/exams/{exam['id']}/", {"status": "published"}, format="json")
    assert Message.objects.filter(kind="result").count() == 2


def test_homework_alerts_and_notice(api, admin_a, make_user, ms):
    api = auth(api, admin_a)
    api.post("/api/homework/", {"section": ms["sec"].pk, "date": str(ms["today"]), "title": "Read chapter 2"}, format="json")
    assert Message.objects.count() == 0  # homework alerts are off by default
    api.patch("/api/messages/settings/", {"homework_alerts": True}, format="json")
    api.post("/api/homework/", {"section": ms["sec"].pk, "date": str(ms["today"]), "title": "Exercise 3"}, format="json")
    assert Message.objects.filter(kind="homework").count() == 3
    assert api.post("/api/messages/notice/", {"text": "School closed tomorrow."}, format="json").json() == {"created": 3}
    assert Message.objects.filter(kind="notice").first().body.endswith(": School closed tomorrow.")
    assert auth(api, make_user("t", Role.TEACHER, ms["sec"].tenant)).get("/api/messages/").status_code == 403


def test_isolation(api, admin_a, admin_b, ms):
    mark(auth(api, admin_a), ms, {"Ali": "absent"})
    assert auth(api, admin_b).get("/api/messages/").json()["count"] == 0


def test_twilio_request_format(monkeypatch):
    import base64
    import io
    import urllib.error
    import urllib.parse

    from apps.messaging.models import MessagingSettings

    seen = {}

    class Response:
        status = 201

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(request, timeout):
        seen["url"], seen["data"], seen["auth"] = request.full_url, urllib.parse.parse_qs(request.data.decode()), request.get_header("Authorization")
        return Response()

    monkeypatch.setattr(services.urllib.request, "urlopen", fake_urlopen)
    cfg = MessagingSettings(channel="twilio_whatsapp", twilio_account_sid="AC1", twilio_auth_token="tok", twilio_from="+14155238886")
    assert services.twilio_send(cfg, "+923001234567", "Hello") == (True, "")
    assert seen["url"] == "https://api.twilio.com/2010-04-01/Accounts/AC1/Messages.json"
    assert seen["data"] == {"To": ["whatsapp:+923001234567"], "From": ["whatsapp:+14155238886"], "Body": ["Hello"]}
    assert seen["auth"] == "Basic " + base64.b64encode(b"AC1:tok").decode()

    def failing(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 400, "Bad", {}, io.BytesIO(b'{"message": "Invalid To number"}'))

    monkeypatch.setattr(services.urllib.request, "urlopen", failing)
    assert services.twilio_send(cfg, "+92", "x") == (False, "Twilio 400: Invalid To number")

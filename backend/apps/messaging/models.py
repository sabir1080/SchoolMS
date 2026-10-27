from django.conf import settings
from django.db import models

from apps.core.models import TenantScopedModel


class Channel(models.TextChoices):
    WHATSAPP_LINK = "whatsapp_link", "WhatsApp (send from your phone, free)"
    TWILIO_SMS = "twilio_sms", "SMS via Twilio (automatic)"
    TWILIO_WHATSAPP = "twilio_whatsapp", "WhatsApp via Twilio (automatic)"


AUTOMATIC = (Channel.TWILIO_SMS, Channel.TWILIO_WHATSAPP)


class MessagingSettings(TenantScopedModel):
    """How an institute sends alerts to parents, and which alerts are on. Secrets are never sent back by the API."""

    channel = models.CharField(max_length=20, choices=Channel.choices, default=Channel.WHATSAPP_LINK)
    twilio_account_sid = models.CharField(max_length=64, blank=True)
    twilio_auth_token = models.CharField(max_length=64, blank=True)
    twilio_from = models.CharField(max_length=30, blank=True, help_text="Twilio phone or WhatsApp sender number, e.g. +14155238886")
    absent_alerts = models.BooleanField(default=True)
    result_alerts = models.BooleanField(default=True)
    homework_alerts = models.BooleanField(default=False)
    payment_alerts = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["tenant"], name="one_messaging_settings_per_tenant")]

    @property
    def is_automatic(self):
        return self.channel in AUTOMATIC and bool(self.twilio_account_sid and self.twilio_auth_token and self.twilio_from)


class Kind(models.TextChoices):
    ABSENT = "absent", "Absent alert"
    FEE = "fee", "Fee reminder"
    RESULT = "result", "Result"
    HOMEWORK = "homework", "Homework"
    NOTICE = "notice", "Notice"
    PAYMENT = "payment", "Fee received"


class Status(models.TextChoices):
    PENDING = "pending", "To send"
    SENT = "sent", "Sent"
    FAILED = "failed", "Failed"


class Message(TenantScopedModel):
    """One text to one parent (or student). Pending messages wait in the outbox."""

    student = models.ForeignKey("students.Student", on_delete=models.SET_NULL, null=True, blank=True, related_name="messages")
    recipient = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    body = models.TextField()
    kind = models.CharField(max_length=20, choices=Kind.choices)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    channel = models.CharField(max_length=20, choices=Channel.choices)
    error = models.CharField(max_length=255, blank=True)
    # Stops the same alert going twice (e.g. "absent:<student>:<date>").
    dedupe_key = models.CharField(max_length=100, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["tenant", "dedupe_key"], condition=~models.Q(dedupe_key=""), name="unique_message_key"),
        ]

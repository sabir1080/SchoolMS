from django.db.models import Count
from django.utils import timezone
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.academics.models import Section
from apps.accounts.models import Role
from apps.core.mixins import TenantScopedViewSetMixin
from apps.core.permissions import HasRole
from apps.core.serializers import TenantPrimaryKeyRelatedField
from apps.subscriptions.features import Feature
from apps.subscriptions.gating import ActiveSubscription, RequiresFeature

from . import alerts, push
from .models import AUTOMATIC, Channel, Message, MessagingSettings, PushSubscription, Status
from .services import normalize_phone, send, settings_for, twilio_send, whatsapp_link


class AdminAlertsView(APIView):
    required_feature = Feature.SMS_ALERTS

    def get_permissions(self):
        return [HasRole.for_roles(Role.ADMIN)(), ActiveSubscription(), RequiresFeature()]


class SettingsSerializer(serializers.ModelSerializer):
    twilio_auth_token = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = MessagingSettings
        fields = ["channel", "twilio_account_sid", "twilio_auth_token", "twilio_from", "absent_alerts", "result_alerts", "homework_alerts",
                  "payment_alerts"]

    def validate_twilio_from(self, value):
        value = value.strip()
        if value and not normalize_phone(value, "XX"):
            raise serializers.ValidationError("Use the full number with country code, e.g. +14155238886.")
        return value

    def validate(self, attrs):
        channel = attrs.get("channel", self.instance.channel)
        if channel in AUTOMATIC:
            sid = attrs.get("twilio_account_sid", self.instance.twilio_account_sid)
            token = attrs.get("twilio_auth_token") or self.instance.twilio_auth_token
            sender = attrs.get("twilio_from", self.instance.twilio_from)
            if not (sid and token and sender):
                raise serializers.ValidationError("Twilio needs the Account SID, Auth Token and sender number.")
        if not attrs.get("twilio_auth_token"):
            attrs.pop("twilio_auth_token", None)  # empty means "keep the saved token"
        return attrs

    def to_representation(self, obj):
        data = super().to_representation(obj)
        data["has_token"] = bool(obj.twilio_auth_token)
        data["is_automatic"] = obj.is_automatic
        data["channels"] = [{"value": c.value, "label": c.label} for c in Channel]
        return data


class MessagingSettingsView(AdminAlertsView):
    def get(self, request):
        return Response(SettingsSerializer(settings_for(request.user.tenant)).data)

    def patch(self, request):
        serializer = SettingsSerializer(settings_for(request.user.tenant), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class MessageSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True, default=None)
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    whatsapp_link = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            "id", "student", "student_name", "recipient", "phone", "body", "kind", "kind_label", "status", "channel",
            "error", "created_at", "sent_at", "whatsapp_link",
        ]

    def get_whatsapp_link(self, message):
        return whatsapp_link(message) if message.phone else None


class NoticeSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=600)
    section = TenantPrimaryKeyRelatedField(queryset=Section.objects.all(), allow_null=True, required=False)


class MessageViewSet(TenantScopedViewSetMixin, mixins.ListModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """The outbox. ?status= and ?kind= filter it."""

    queryset = Message.objects.select_related("student")
    serializer_class = MessageSerializer
    permission_classes = [HasRole.for_roles(Role.ADMIN)]
    required_feature = Feature.SMS_ALERTS

    def get_queryset(self):
        queryset = super().get_queryset()
        for field in ("status", "kind"):
            if self.request.query_params.get(field):
                queryset = queryset.filter(**{field: self.request.query_params[field]})
        return queryset

    def summary(self):
        counts = dict(Message.objects.filter(tenant=self.get_tenant()).order_by().values("status").annotate(n=Count("id")).values_list("status", "n"))
        return {s.value: counts.get(s.value, 0) for s in Status}

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        response.data["summary"] = self.summary()
        response.data["automatic"] = settings_for(self.get_tenant()).is_automatic
        return response

    @action(detail=True, methods=["post"], url_path="mark-sent")
    def mark_sent(self, request, pk=None):
        """The admin sent it from their own WhatsApp."""
        message = self.get_object()
        message.status, message.sent_at, message.error = Status.SENT, timezone.now(), ""
        message.save(update_fields=["status", "sent_at", "error", "updated_at"])
        return Response(MessageSerializer(message).data)

    @action(detail=False, methods=["post"], url_path="send-pending")
    def send_pending(self, request):
        cfg = settings_for(self.get_tenant())
        if not cfg.is_automatic:
            raise ValidationError("Automatic sending is not set up. Choose Twilio in the message settings first.")
        waiting = list(self.get_queryset().filter(status__in=[Status.PENDING, Status.FAILED]).exclude(phone="").order_by("id"))
        sent, failed = send(waiting, cfg)
        return Response({"sent": sent, "failed": failed, "left": max(len(waiting) - sent - failed, 0)})

    @action(detail=False, methods=["post"], url_path="fee-reminders")
    def fee_reminders(self, request):
        created = alerts.fee_reminders(self.get_tenant(), request.user)
        return Response({"created": len(created)})

    @action(detail=False, methods=["post"])
    def notice(self, request):
        serializer = NoticeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        created = alerts.notice(self.get_tenant(), serializer.validated_data["text"].strip(), serializer.validated_data.get("section"), request.user)
        return Response({"created": len(created)})

    @action(detail=False, methods=["post"])
    def test(self, request):
        """Send a test text to a number through the saved Twilio settings."""
        tenant = self.get_tenant()
        cfg = settings_for(tenant)
        phone = normalize_phone(request.data.get("phone", ""), tenant.country)
        if not phone:
            raise ValidationError({"phone": ["Enter a valid mobile number."]})
        if not cfg.is_automatic:
            raise ValidationError("Choose Twilio and save its details first.")
        ok, error = twilio_send(cfg, phone, f"{tenant.name}: test message from SchoolMS.")
        if not ok:
            raise ValidationError(error or "Twilio did not accept the message.")
        return Response({"sent": True})


class PushSubscribeSerializer(serializers.Serializer):
    endpoint = serializers.URLField(max_length=1000)
    keys = serializers.DictField(child=serializers.CharField(max_length=200))

    def validate_endpoint(self, value):
        if not push.endpoint_allowed(value):
            raise serializers.ValidationError("This browser's notification service is not supported.")
        return value

    def validate_keys(self, value):
        if not value.get("p256dh") or not value.get("auth"):
            raise serializers.ValidationError("Missing keys.")
        try:
            if len(push.b64url_decode(value["p256dh"])) != 65 or len(push.b64url_decode(value["auth"])) != 16:
                raise ValueError
        except ValueError:
            raise serializers.ValidationError("Invalid keys.")
        return value


class PushView(APIView):
    """Turn phone notifications on or off for this device, and send a test."""

    def get_permissions(self):
        return [HasRole.for_roles(Role.ADMIN, Role.TEACHER, Role.PARENT, Role.STUDENT)()]

    def get(self, request):
        return Response({
            "enabled": push.enabled(),
            "public_key": push.public_key_b64(),
            "devices": PushSubscription.objects.filter(user=request.user).count(),
        })

    def post(self, request):
        action = request.data.get("action")
        if action == "test":
            subs = list(PushSubscription.objects.filter(user=request.user))
            data = {"title": request.user.tenant.name, "body": "Notifications are working on this device.", "url": "/dashboard/"}
            sent = sum(push.send_one(s, data) for s in subs) if push.enabled() else 0
            return Response({"sent": sent, "devices": len(subs)})
        if action == "unsubscribe":
            PushSubscription.objects.filter(user=request.user, endpoint=request.data.get("endpoint", "")).delete()
            return Response({"devices": PushSubscription.objects.filter(user=request.user).count()})
        if not push.enabled():
            raise ValidationError("Notifications are not set up on this server yet.")
        serializer = PushSubscribeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        PushSubscription.objects.update_or_create(
            endpoint=d["endpoint"],
            defaults={"tenant": request.user.tenant, "user": request.user, "p256dh": d["keys"]["p256dh"], "auth": d["keys"]["auth"],
                      "user_agent": request.META.get("HTTP_USER_AGENT", "")[:255], "last_error": ""},
        )
        return Response({"devices": PushSubscription.objects.filter(user=request.user).count()}, status=201)

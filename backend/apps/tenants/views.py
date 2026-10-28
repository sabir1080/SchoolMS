from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.generics import RetrieveAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Role
from apps.accounts.serializers import SetPasswordSerializer, issue_tokens
from apps.agreements.models import SignedAgreement
from apps.agreements.models import Status as AgreementStatus
from apps.agreements.services import accept_trial, activate, pending_for
from apps.core.permissions import IsInstituteAdmin, IsSuperAdmin
from apps.subscriptions.gating import ActiveSubscription
from apps.subscriptions.serializers import (
    RecordPaymentSerializer,
    SubscriptionPaymentSerializer,
    SubscriptionUpdateSerializer,
)
from apps.subscriptions.services import record_payment

from .models import Tenant
from .serializers import (
    InstituteRegistrationSerializer,
    InstituteSettingsSerializer,
    PublicInstituteSerializer,
    ResetAdminPasswordSerializer,
    TenantSerializer,
)
from .services import create_institute
from .validators import normalize_code


class TenantViewSet(viewsets.ModelViewSet):
    """Platform owner (super admin) manages institutes and their subscriptions here."""

    queryset = Tenant.objects.select_related("subscription__plan").prefetch_related(
        "subscription__plan__prices", "users"
    )
    permission_classes = [IsSuperAdmin]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_serializer_class(self):
        return InstituteRegistrationSerializer if self.action == "create" else TenantSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tenant_fields, admin = serializer.split()
        tenant, _ = create_institute(admin=admin, **tenant_fields)
        return Response(TenantSerializer(tenant).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["patch"])
    def subscription(self, request, pk=None):
        tenant = self.get_object()
        serializer = SubscriptionUpdateSerializer(tenant.subscription, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(TenantSerializer(self.get_object()).data)

    @action(detail=True, methods=["post"], url_path="record-payment")
    def record_payment(self, request, pk=None):
        tenant = self.get_object()
        serializer = RecordPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        agreement_id = request.data.get("agreement")
        agreement = None
        if agreement_id:
            agreement = SignedAgreement.objects.filter(tenant=tenant, pk=agreement_id, status=AgreementStatus.PENDING).first()
            if agreement is None:
                raise ValidationError({"agreement": ["No agreement waiting for payment with this number."]})
        with transaction.atomic():
            subscription = record_payment(tenant.subscription, recorded_by=request.user, **data)
            payment = subscription.payments.order_by("-created_at", "-id").first()
            agreement = agreement or pending_for(tenant, data["plan"], data["billing_cycle"])
            if agreement is not None:
                activate(agreement, payment)
        return Response({**TenantSerializer(self.get_object()).data, "agreement": agreement.pk if agreement else None})

    @action(detail=True, methods=["post"], url_path="reset-admin-password")
    def reset_admin_password(self, request, pk=None):
        """Set a new password for one of the institute's admins (e.g. when they forgot it)."""
        tenant = self.get_object()
        data = ResetAdminPasswordSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        admin = tenant.users.filter(role=Role.ADMIN, username=data.validated_data["username"]).first()
        if admin is None:
            raise NotFound("No admin with this username in this institute.")
        serializer = SetPasswordSerializer(data={"new_password": data.validated_data["new_password"]}, context={"user": admin})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Password updated."})

    @action(detail=True, methods=["get"])
    def payments(self, request, pk=None):
        tenant = self.get_object()
        return Response(SubscriptionPaymentSerializer(tenant.subscription.payments.all(), many=True).data)


class InstituteLookupView(RetrieveAPIView):
    """Login screen step 1: check an institute code and show the institute's name."""

    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = PublicInstituteSerializer
    throttle_scope = "lookup"

    def get_object(self):
        tenant = Tenant.objects.filter(slug=normalize_code(self.kwargs["code"])).first()
        if tenant is None:
            raise NotFound("Institute code not found.")
        if not tenant.is_active:
            raise PermissionDenied("This institute account is suspended.")
        return tenant


class InstituteRegistrationView(APIView):
    """Self-service sign-up: creates the institute, its admin and a free trial, then logs the admin in."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_scope = "register"

    def post(self, request):
        serializer = InstituteRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if request.data.get("accept_terms") is not True:
            raise ValidationError({"accept_terms": ["Please read and accept the free trial agreement."]})
        tenant_fields, admin = serializer.split()
        tenant_fields.pop("is_active", None)
        with transaction.atomic():
            tenant, user = create_institute(admin=admin, **tenant_fields)
            signer = user.get_full_name() or user.username
            accept_trial(tenant, user, request, signer)
        return Response(issue_tokens(user), status=status.HTTP_201_CREATED)


class InstituteSettingsView(RetrieveUpdateAPIView):
    """Institute admin views and edits their institute's details and password policy."""

    serializer_class = InstituteSettingsSerializer
    permission_classes = [IsInstituteAdmin, ActiveSubscription]
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return self.request.user.tenant

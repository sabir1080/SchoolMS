from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.serializers import issue_tokens
from apps.core.permissions import IsSuperAdmin
from apps.subscriptions.serializers import (
    RecordPaymentSerializer,
    SubscriptionPaymentSerializer,
    SubscriptionUpdateSerializer,
)
from apps.subscriptions.services import record_payment

from .models import Tenant
from .serializers import InstituteRegistrationSerializer, PublicInstituteSerializer, TenantSerializer
from .services import create_institute
from .validators import normalize_code


class TenantViewSet(viewsets.ModelViewSet):
    """Platform owner (super admin) manages institutes and their subscriptions here."""

    queryset = Tenant.objects.select_related("subscription__plan").prefetch_related("subscription__plan__prices")
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
        record_payment(tenant.subscription, recorded_by=request.user, **serializer.validated_data)
        return Response(TenantSerializer(self.get_object()).data)

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
        tenant_fields, admin = serializer.split()
        tenant_fields.pop("is_active", None)
        _, user = create_institute(admin=admin, **tenant_fields)
        return Response(issue_tokens(user), status=status.HTTP_201_CREATED)

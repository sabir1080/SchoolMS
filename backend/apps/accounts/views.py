from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.core.mixins import TenantScopedViewSetMixin
from apps.core.permissions import IsInstituteAdmin
from apps.subscriptions.gating import check_limit

from .models import STAFF_ROLES, User
from .throttles import LoginAccountThrottle, LoginIPThrottle
from .serializers import (
    ChangePasswordSerializer,
    InstituteLoginSerializer,
    MeSerializer,
    PlatformLoginSerializer,
    SetPasswordSerializer,
    UserSerializer,
)


class LoginView(GenericAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [LoginAccountThrottle, LoginIPThrottle]

    def get_authenticate_header(self, request):
        # Makes DRF answer failed logins with 401 instead of 403.
        return 'Bearer realm="api"'

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)


class InstituteLoginView(LoginView):
    serializer_class = InstituteLoginSerializer


class PlatformLoginView(LoginView):
    serializer_class = PlatformLoginSerializer


class MeView(RetrieveAPIView):
    serializer_class = MeSerializer

    def get_object(self):
        return self.request.user


class ChangePasswordView(GenericAPIView):
    """Any logged-in user (including super admins) changes their own password."""

    serializer_class = ChangePasswordSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Password changed."})


# Which plan limit applies to each role. Students are limited by their admission
# records (apps.students), not by their logins.
LIMIT_FOR_ROLE = {role: ("max_staff", STAFF_ROLES) for role in STAFF_ROLES}


class UserViewSet(TenantScopedViewSetMixin, viewsets.ModelViewSet):
    """Institute admins manage admins, teachers, students and parents here."""

    queryset = User.objects.select_related("tenant").order_by("first_name", "last_name", "username")
    serializer_class = UserSerializer
    permission_classes = [IsInstituteAdmin]

    def get_queryset(self):
        queryset = super().get_queryset()
        role = self.request.query_params.get("role")
        if role:
            queryset = queryset.filter(role=role)
        return queryset

    def check_plan_limit(self, role, exclude=None):
        if role not in LIMIT_FOR_ROLE:
            return
        limit_field, counted_roles = LIMIT_FOR_ROLE[role]
        active = User.objects.filter(tenant=self.get_tenant(), role__in=counted_roles, is_active=True)
        if exclude is not None:
            active = active.exclude(pk=exclude.pk)
        check_limit(self.get_tenant(), limit_field, active.count())

    def perform_create(self, serializer):
        if serializer.validated_data.get("is_active", True):
            self.check_plan_limit(serializer.validated_data["role"])
        super().perform_create(serializer)

    def perform_update(self, serializer):
        instance = serializer.instance
        role = serializer.validated_data.get("role", instance.role)
        is_active = serializer.validated_data.get("is_active", instance.is_active)
        counted_before = instance.is_active and LIMIT_FOR_ROLE.get(instance.role) == LIMIT_FOR_ROLE.get(role)
        if is_active and not counted_before:
            self.check_plan_limit(role, exclude=instance)
        serializer.save()

    @action(detail=True, methods=["post"], url_path="set-password")
    def set_password(self, request, pk=None):
        serializer = SetPasswordSerializer(data=request.data, context={"user": self.get_object()})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Password updated."})

    def perform_destroy(self, instance):
        # Deactivate instead of deleting so attendance, fees etc. keep their history.
        if instance == self.request.user:
            raise ValidationError("You cannot deactivate your own account.")
        instance.is_active = False
        instance.save(update_fields=["is_active"])

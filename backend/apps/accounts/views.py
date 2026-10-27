from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.generics import RetrieveAPIView
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.core.mixins import TenantScopedViewSetMixin
from apps.core.permissions import IsInstituteAdmin

from .models import User
from .serializers import LoginSerializer, MeSerializer, UserSerializer


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer


class MeView(RetrieveAPIView):
    serializer_class = MeSerializer

    def get_object(self):
        return self.request.user


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

    def perform_destroy(self, instance):
        # Deactivate instead of deleting so attendance, fees etc. keep their history.
        if instance == self.request.user:
            raise ValidationError("You cannot deactivate your own account.")
        instance.is_active = False
        instance.save(update_fields=["is_active"])

from rest_framework import viewsets

from apps.core.permissions import IsSuperAdmin

from .models import Tenant
from .serializers import TenantCreateSerializer, TenantSerializer


class TenantViewSet(viewsets.ModelViewSet):
    """Platform owner (super admin) manages institutes here."""

    queryset = Tenant.objects.all()
    permission_classes = [IsSuperAdmin]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_serializer_class(self):
        return TenantCreateSerializer if self.action == "create" else TenantSerializer

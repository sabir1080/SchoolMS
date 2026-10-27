from rest_framework.exceptions import PermissionDenied

from apps.subscriptions.gating import ActiveSubscription, RequiresFeature


class TenantScopedViewSetMixin:
    """Restrict a viewset to the requesting user's institute and its plan.

    Every query is filtered by ``request.user.tenant`` and new rows are always
    saved with that tenant, so one institute can never read or write another
    institute's data through the API.

    The institute also needs a usable subscription, and when ``required_feature``
    is set (see ``apps.subscriptions.features.Feature``) its plan must include it.
    """

    required_feature = None

    def get_permissions(self):
        return [*super().get_permissions(), ActiveSubscription(), RequiresFeature()]

    def get_tenant(self):
        tenant = getattr(self.request.user, "tenant", None)
        if tenant is None:
            raise PermissionDenied("This endpoint is only available to institute users.")
        return tenant

    def get_queryset(self):
        return super().get_queryset().filter(tenant=self.get_tenant())

    def perform_create(self, serializer):
        serializer.save(tenant=self.get_tenant())

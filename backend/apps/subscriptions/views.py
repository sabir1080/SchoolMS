from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny

from .gating import get_subscription
from .models import Plan
from .serializers import PlanSerializer, SubscriptionSerializer


class PublicPlanListView(ListAPIView):
    """Plans shown on the registration and billing pages."""

    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = PlanSerializer
    pagination_class = None
    queryset = Plan.objects.filter(is_active=True, is_public=True).prefetch_related("prices")


class MySubscriptionView(RetrieveAPIView):
    """The logged-in user's institute subscription. Works even after it expires."""

    serializer_class = SubscriptionSerializer

    def get_object(self):
        tenant = self.request.user.tenant
        if tenant is None:
            raise PermissionDenied("Only institute users have a subscription.")
        subscription = get_subscription(tenant)
        if subscription is None:
            raise NotFound("No subscription found.")
        return subscription

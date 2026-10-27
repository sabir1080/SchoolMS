"""Plan enforcement: active subscription, plan features and plan limits.

Feature viewsets get this automatically through ``TenantScopedViewSetMixin``.
"""

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.permissions import BasePermission


class PaymentRequired(APIException):
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    default_detail = "Your subscription does not allow this."
    default_code = "payment_required"


def get_subscription(tenant):
    try:
        return tenant.subscription
    except tenant._meta.model.subscription.RelatedObjectDoesNotExist:
        return None


class ActiveSubscription(BasePermission):
    """Institute users need a trial or paid subscription that has not run out."""

    def has_permission(self, request, view):
        tenant = getattr(request.user, "tenant", None)
        if tenant is None:
            return True
        subscription = get_subscription(tenant)
        if subscription is None or not subscription.is_usable:
            raise PaymentRequired(
                "Your institute's subscription has expired. Please renew it to continue.",
                code="subscription_inactive",
            )
        return True


class RequiresFeature(BasePermission):
    """The institute's plan must include ``view.required_feature``."""

    def has_permission(self, request, view):
        feature = getattr(view, "required_feature", None)
        tenant = getattr(request.user, "tenant", None)
        if feature is None or tenant is None:
            return True
        subscription = get_subscription(tenant)
        if subscription is None or not subscription.plan.has_feature(feature):
            raise PaymentRequired(
                "This module is not included in your plan. Please upgrade to use it.",
                code="feature_not_in_plan",
            )
        return True


def check_limit(tenant, limit_field, current_count):
    """Raise if adding one more item would exceed the plan's ``limit_field`` (e.g. ``max_students``)."""
    subscription = get_subscription(tenant)
    limit = getattr(subscription.plan, limit_field) if subscription else 0
    if limit is not None and current_count >= limit:
        raise PaymentRequired(
            f"Your plan allows up to {limit}. Please upgrade to add more.",
            code="plan_limit_reached",
        )

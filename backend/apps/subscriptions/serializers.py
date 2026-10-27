from rest_framework import serializers

from apps.accounts.models import STAFF_ROLES, Role

from .features import Feature
from .models import BillingCycle, PaymentMethod, Plan, PlanPrice, Subscription, SubscriptionPayment


class PlanPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanPrice
        fields = ["currency", "billing_cycle", "amount"]


class PlanSerializer(serializers.ModelSerializer):
    prices = PlanPriceSerializer(many=True, read_only=True)
    feature_labels = serializers.SerializerMethodField()

    class Meta:
        model = Plan
        fields = [
            "id", "code", "name", "description", "max_students", "max_staff",
            "features", "feature_labels", "prices",
        ]

    def get_feature_labels(self, plan):
        labels = dict(Feature.choices)
        return [labels[f] for f in plan.features if f in labels]


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)
    effective_status = serializers.CharField(read_only=True)
    is_usable = serializers.BooleanField(read_only=True)
    days_left = serializers.IntegerField(read_only=True)
    usage = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = [
            "plan", "status", "effective_status", "is_usable", "billing_cycle",
            "current_period_start", "current_period_end", "days_left", "usage",
        ]

    def get_usage(self, subscription):
        active = subscription.tenant.users.filter(is_active=True)
        return {
            "students": active.filter(role=Role.STUDENT).count(),
            "staff": active.filter(role__in=STAFF_ROLES).count(),
        }


class SubscriptionPaymentSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source="plan.name", read_only=True)

    class Meta:
        model = SubscriptionPayment
        fields = [
            "id", "plan_name", "billing_cycle", "amount", "currency", "method",
            "reference", "notes", "period_start", "period_end", "created_at",
        ]


class SubscriptionUpdateSerializer(serializers.ModelSerializer):
    """Super admin corrections: change plan, status or end date directly."""

    plan = serializers.SlugRelatedField(slug_field="code", queryset=Plan.objects.filter(is_active=True))

    class Meta:
        model = Subscription
        fields = ["plan", "status", "billing_cycle", "current_period_end"]


class RecordPaymentSerializer(serializers.Serializer):
    plan = serializers.SlugRelatedField(slug_field="code", queryset=Plan.objects.filter(is_active=True))
    billing_cycle = serializers.ChoiceField(choices=BillingCycle.choices)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    currency = serializers.CharField(max_length=3)
    method = serializers.ChoiceField(choices=PaymentMethod.choices)
    reference = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_currency(self, value):
        return value.upper()

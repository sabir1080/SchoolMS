from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import Plan, Subscription, SubscriptionPayment, SubscriptionStatus


def start_trial(tenant):
    """Give a new institute a free trial on the configured trial plan."""
    plan = Plan.objects.get(code=settings.TRIAL_PLAN_CODE)
    now = timezone.now()
    return Subscription.objects.create(
        tenant=tenant,
        plan=plan,
        status=SubscriptionStatus.TRIALING,
        current_period_start=now,
        current_period_end=now + timedelta(days=settings.TRIAL_DAYS),
    )


@transaction.atomic
def record_payment(subscription, *, plan, billing_cycle, amount, currency, method, reference="", notes="", recorded_by=None):
    """Record a manual payment, switch to ``plan`` and extend the subscription by one cycle."""
    subscription = Subscription.objects.select_for_update().get(pk=subscription.pk)
    subscription.plan = plan
    subscription.extend(billing_cycle)
    subscription.save()
    SubscriptionPayment.objects.create(
        subscription=subscription,
        plan=plan,
        billing_cycle=billing_cycle,
        amount=amount,
        currency=currency,
        method=method,
        reference=reference,
        notes=notes,
        period_start=subscription.current_period_start,
        period_end=subscription.current_period_end,
        recorded_by=recorded_by,
    )
    return subscription

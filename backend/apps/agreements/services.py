from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.subscriptions.features import Feature

from . import texts
from .models import Kind, ProviderProfile, SignedAgreement, Status


def provider_snapshot():
    p = ProviderProfile.get()
    return {
        "business_name": p.business_name, "owner_name": p.owner_name, "address": p.address, "phone": p.phone,
        "email": p.email, "grace_days": p.grace_days, "data_retention_days": p.data_retention_days,
        "refund_policy": p.refund_policy,
    }


def client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return (forwarded.split(",")[0].strip() or request.META.get("REMOTE_ADDR", ""))[:60]


def trial_document():
    provider = provider_snapshot()
    return {"kind": Kind.TRIAL, "version": texts.TRIAL_VERSION, "provider": provider, "schedule": {"trial_days": settings.TRIAL_DAYS},
            "sections": texts.trial_sections(provider, settings.TRIAL_DAYS)}


def price_for(plan, cycle, currency):
    prices = {(p.currency, p.billing_cycle): p.amount for p in plan.prices.all()}
    if (currency, cycle) in prices:
        return prices[(currency, cycle)], currency
    if ("USD", cycle) in prices:
        return prices[("USD", cycle)], "USD"
    return None, currency


def subscription_document(plan, cycle, currency):
    amount, currency = price_for(plan, cycle, currency)
    labels = dict(Feature.choices)
    provider = provider_snapshot()
    schedule = texts.schedule_for(plan, cycle, amount, currency, [labels[f] for f in plan.features if f in labels])
    return {"kind": Kind.SUBSCRIPTION, "version": texts.SUBSCRIPTION_VERSION, "provider": provider, "schedule": schedule,
            "sections": texts.subscription_sections(provider, schedule), "amount": amount, "currency": currency}


def accept_trial(tenant, user, request, signer_name, institute_name=None):
    """Record that the institute accepted the free trial agreement."""
    doc = trial_document()
    return SignedAgreement.objects.create(
        tenant=tenant, kind=Kind.TRIAL, version=doc["version"], status=Status.ACCEPTED,
        institute_legal_name=institute_name or tenant.name, institute_address=tenant.address,
        signer_name=signer_name, signature=signer_name, signer_phone=tenant.phone, signed_by=user,
        ip_address=client_ip(request), user_agent=request.META.get("HTTP_USER_AGENT", "")[:255],
        provider=doc["provider"], schedule=doc["schedule"], sections=doc["sections"],
    )


@transaction.atomic
def sign_subscription(tenant, user, request, plan, cycle, details):
    """The institute signs a subscription agreement; it waits for payment. Older unpaid ones are cancelled."""
    doc = subscription_document(plan, cycle, tenant.currency)
    SignedAgreement.objects.filter(tenant=tenant, status=Status.PENDING).update(status=Status.CANCELLED)
    return SignedAgreement.objects.create(
        tenant=tenant, kind=Kind.SUBSCRIPTION, version=doc["version"], status=Status.PENDING, plan=plan,
        billing_cycle=cycle, amount=doc["amount"], currency=doc["currency"], signed_by=user,
        ip_address=client_ip(request), user_agent=request.META.get("HTTP_USER_AGENT", "")[:255],
        provider=doc["provider"], schedule=doc["schedule"], sections=doc["sections"], **details,
    )


def pending_for(tenant, plan=None, cycle=None):
    pending = SignedAgreement.objects.filter(tenant=tenant, status=Status.PENDING)
    if plan is not None:
        pending = pending.filter(plan=plan, billing_cycle=cycle)
    return pending.first()


@transaction.atomic
def activate(agreement, payment):
    """The platform owner recorded the payment: this agreement now covers the paid period."""
    SignedAgreement.objects.filter(tenant=agreement.tenant, kind=Kind.SUBSCRIPTION, status=Status.ACTIVE).update(
        status=Status.SUPERSEDED
    )
    agreement.status = Status.ACTIVE
    agreement.payment = payment
    # The period this payment bought (a renewal starts where the previous period ended).
    agreement.period_end = payment.period_end
    agreement.period_start = payment.period_end - timedelta(days=365 if payment.billing_cycle == "yearly" else 30)
    agreement.activated_at = timezone.now()
    agreement.save()
    return agreement

from apps.subscriptions.features import Feature


def admissions_open(tenant):
    """The public form takes applications only when the admin opened it and the plan includes it."""
    subscription = getattr(tenant, "subscription", None)
    return bool(
        tenant.is_active and tenant.admissions_open and subscription and subscription.is_usable
        and Feature.ADMISSIONS in subscription.plan.features
    )

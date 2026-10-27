from decimal import Decimal

from django.db import migrations

# Starting plans. Prices and limits are placeholders the platform owner can edit
# in the Django admin (/admin) at any time.
PLANS = [
    {
        "code": "basic",
        "name": "Basic",
        "description": "For small schools, tuition and coaching centers",
        "max_students": 200,
        "max_staff": 20,
        "features": ["academics", "students", "attendance", "fees"],
        "prices": {"PKR": ("3000", "30000"), "USD": ("15", "150")},
    },
    {
        "code": "pro",
        "name": "Pro",
        "description": "For growing institutes that collect fees online",
        "max_students": 1000,
        "max_staff": 100,
        "features": ["academics", "students", "attendance", "fees", "online_payments", "reports", "sms_alerts"],
        "prices": {"PKR": ("7000", "70000"), "USD": ("35", "350")},
    },
    {
        "code": "enterprise",
        "name": "Enterprise",
        "description": "Unlimited students and staff for colleges and universities",
        "max_students": None,
        "max_staff": None,
        "features": [
            "academics", "students", "attendance", "fees", "online_payments", "reports", "sms_alerts", "white_label",
        ],
        "prices": {"PKR": ("15000", "150000"), "USD": ("79", "790")},
    },
]


def create_plans(apps, schema_editor):
    Plan = apps.get_model("subscriptions", "Plan")
    PlanPrice = apps.get_model("subscriptions", "PlanPrice")
    for order, data in enumerate(PLANS):
        data = dict(data)
        prices = data.pop("prices")
        plan, _ = Plan.objects.update_or_create(code=data.pop("code"), defaults={**data, "sort_order": order})
        for currency, (monthly, yearly) in prices.items():
            for cycle, amount in (("monthly", monthly), ("yearly", yearly)):
                PlanPrice.objects.update_or_create(
                    plan=plan, currency=currency, billing_cycle=cycle, defaults={"amount": Decimal(amount)}
                )


class Migration(migrations.Migration):
    dependencies = [("subscriptions", "0001_initial")]

    operations = [migrations.RunPython(create_plans, migrations.RunPython.noop)]

from django.db import migrations

PLANS = ["basic", "pro", "enterprise"]


def add_module(apps, schema_editor):
    Plan = apps.get_model("subscriptions", "Plan")
    for plan in Plan.objects.filter(code__in=PLANS):
        if "admissions" not in plan.features:
            plan.features = [*plan.features, "admissions"]
            plan.save(update_fields=["features"])


class Migration(migrations.Migration):
    dependencies = [("subscriptions", "0009_alter_plan_features")]

    operations = [migrations.RunPython(add_module, migrations.RunPython.noop)]

from django.db import migrations

NEW = {"basic": ["certificates"], "pro": ["certificates", "white_label"], "enterprise": ["certificates", "white_label"]}


def add_modules(apps, schema_editor):
    Plan = apps.get_model("subscriptions", "Plan")
    for plan in Plan.objects.filter(code__in=NEW):
        plan.features = [*plan.features, *[f for f in NEW[plan.code] if f not in plan.features]]
        plan.save(update_fields=["features"])


class Migration(migrations.Migration):
    dependencies = [("subscriptions", "0006_alter_plan_features")]

    operations = [migrations.RunPython(add_modules, migrations.RunPython.noop)]

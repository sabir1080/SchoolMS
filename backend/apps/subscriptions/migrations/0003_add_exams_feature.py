from django.db import migrations


def add_exams(apps, schema_editor):
    Plan = apps.get_model("subscriptions", "Plan")
    for plan in Plan.objects.filter(code__in=["basic", "pro", "enterprise"]):
        if "exams" not in plan.features:
            plan.features = [*plan.features, "exams"]
            plan.save(update_fields=["features"])


class Migration(migrations.Migration):
    dependencies = [("subscriptions", "0002_default_plans")]

    operations = [migrations.RunPython(add_exams, migrations.RunPython.noop)]

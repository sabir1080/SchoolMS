from django.db import migrations

NEW = {"basic": ["timetable", "homework"], "pro": ["timetable", "homework", "payroll"], "enterprise": ["timetable", "homework", "payroll"]}


def add_modules(apps, schema_editor):
    Plan = apps.get_model("subscriptions", "Plan")
    for plan in Plan.objects.filter(code__in=NEW):
        plan.features = [*plan.features, *[f for f in NEW[plan.code] if f not in plan.features]]
        plan.save(update_fields=["features"])


class Migration(migrations.Migration):
    dependencies = [("subscriptions", "0004_exams_feature_choice")]

    operations = [migrations.RunPython(add_modules, migrations.RunPython.noop)]

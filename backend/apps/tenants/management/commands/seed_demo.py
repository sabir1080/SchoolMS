from django.core.management.base import BaseCommand

from apps.tenants.demo import DEMO_CODE, DEMO_PASSWORD, seed_demo, wipe_institutes


class Command(BaseCommand):
    help = "Create the demo institute (code 'demo'). With --wipe-all, first delete ALL institutes and their data."

    def add_arguments(self, parser):
        parser.add_argument("--wipe-all", action="store_true", help="Delete every institute first (super admins and plans stay).")

    def handle(self, *args, wipe_all=False, **options):
        if wipe_all:
            count, _ = wipe_institutes()
            self.stdout.write(f"Deleted {count} institute(s) and their data.")
        tenant = seed_demo()
        self.stdout.write(self.style.SUCCESS(
            f"Demo institute '{tenant.name}' ready: code '{DEMO_CODE}', users admin/sana/rashid/ahmed, password '{DEMO_PASSWORD}'."
        ))

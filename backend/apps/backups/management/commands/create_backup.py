import shutil

from django.core.management.base import BaseCommand

from apps.backups.services import backup_summary, create_backup


class Command(BaseCommand):
    help = "Write a full backup (all institutes) to a compressed JSON file."

    def add_arguments(self, parser):
        parser.add_argument("output", help="Where to save the .json.gz file")

    def handle(self, output, **options):
        path = create_backup()
        shutil.move(path, output)
        counts = backup_summary(output)
        self.stdout.write(f"Saved {output}: {sum(counts.values())} rows, {counts.get('tenants.tenant', 0)} institutes.")

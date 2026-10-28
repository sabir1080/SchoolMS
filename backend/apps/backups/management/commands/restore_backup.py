from django.core.management.base import BaseCommand, CommandError

from apps.backups.services import restore_backup


class Command(BaseCommand):
    help = "Restore a full backup into an empty, migrated database."

    def add_arguments(self, parser):
        parser.add_argument("backup", help="The .json.gz file made by create_backup or the platform's download")

    def handle(self, backup, **options):
        try:
            counts = restore_backup(backup)
        except ValueError as err:
            raise CommandError(str(err))
        self.stdout.write(f"Restored {sum(counts.values())} rows, {counts.get('tenants.tenant', 0)} institutes.")

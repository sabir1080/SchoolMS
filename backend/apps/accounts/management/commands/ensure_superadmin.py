import os

from django.core.management.base import BaseCommand

from apps.accounts.models import User


class Command(BaseCommand):
    """Create the platform super admin from environment variables if it does not exist.

    Runs on every deploy so a super admin can be created without shell access
    (Render's free plan has no shell). Existing accounts are never changed.
    """

    help = "Create the super admin from SUPERADMIN_USERNAME / SUPERADMIN_EMAIL / SUPERADMIN_PASSWORD."

    def handle(self, *args, **options):
        username = os.environ.get("SUPERADMIN_USERNAME")
        password = os.environ.get("SUPERADMIN_PASSWORD")
        email = os.environ.get("SUPERADMIN_EMAIL", "")
        if not username or not password:
            self.stdout.write("SUPERADMIN_USERNAME/SUPERADMIN_PASSWORD not set; skipping.")
            return
        if User.objects.filter(username=username).exists():
            self.stdout.write(f"Super admin '{username}' already exists.")
            return
        User.objects.create_superuser(username, email, password)
        self.stdout.write(self.style.SUCCESS(f"Created super admin '{username}'."))

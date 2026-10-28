"""Full backups of every institute's data as one compressed JSON file, and restoring them.

The file holds everything needed to rebuild the platform on an empty, migrated database: institutes,
users (password hashes), students, fees, results and settings, including payment gateway keys, so it
must be kept private.
"""

import gzip
import json
import os
import tempfile

from django.core.management import call_command
from django.db import transaction

# Rebuilt by `migrate` itself, or not worth keeping.
EXCLUDE = ["contenttypes", "auth.permission", "admin.logentry", "sessions", "backups"]


def create_backup(directory=None):
    """Write a backup to a new ``.json.gz`` file and return its path."""
    handle, path = tempfile.mkstemp(prefix="schoolms-backup-", suffix=".json.gz", dir=directory)
    os.close(handle)
    # Plain ids (not natural keys): usernames repeat across institutes, so they cannot identify a user.
    call_command("dumpdata", exclude=EXCLUDE, output=path, verbosity=0)
    return path


def backup_summary(path):
    """Rows per model in a backup file (to show what it holds before restoring)."""
    counts = {}
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for row in json.load(fh):
            counts[row["model"]] = counts.get(row["model"], 0) + 1
    return counts


@transaction.atomic
def restore_backup(path):
    """Load a backup into this database (which must have no institutes yet)."""
    from apps.tenants.models import Tenant

    if Tenant.objects.exists():
        raise ValueError("This database already has institutes. Restore only into an empty, migrated database.")
    # Plans and the super admin are created by migrations/startup; the backup brings its own copies.
    from apps.accounts.models import User
    from apps.subscriptions.models import Plan, PlanPrice

    User.objects.all().delete()
    PlanPrice.objects.all().delete()
    Plan.objects.all().delete()
    call_command("loaddata", path, verbosity=0)
    return backup_summary(path)

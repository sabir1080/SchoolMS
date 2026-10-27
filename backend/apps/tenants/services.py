from django.db import transaction

from apps.accounts.models import Role, User
from apps.subscriptions.services import start_trial

from .models import Tenant


@transaction.atomic
def create_institute(*, admin, **tenant_fields):
    """Create an institute, its first admin account and its free trial.

    ``admin`` holds username, email, password and optional first/last name.
    """
    tenant = Tenant.objects.create(**tenant_fields)
    admin = dict(admin)
    password = admin.pop("password")
    user = User.objects.create_user(**admin, password=password, role=Role.ADMIN, tenant=tenant)
    start_trial(tenant)
    return tenant, user

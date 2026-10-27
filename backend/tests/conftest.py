import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.subscriptions.services import start_trial
from apps.tenants.models import Tenant

PASSWORD = "Str0ng-pass-123"


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def make_tenant(db):
    def _make(slug, **kwargs):
        tenant = Tenant.objects.create(name=slug.title(), slug=slug, institute_type="school", **kwargs)
        start_trial(tenant)
        return tenant

    return _make


@pytest.fixture
def make_user(db):
    def _make(username, role, tenant=None, **kwargs):
        return User.objects.create_user(username=username, password=PASSWORD, role=role, tenant=tenant, **kwargs)

    return _make


@pytest.fixture
def super_admin(db):
    return User.objects.create_superuser("owner", "owner@example.com", PASSWORD)


@pytest.fixture
def school_a(make_tenant):
    return make_tenant("alpha")


@pytest.fixture
def school_b(make_tenant):
    return make_tenant("beta")


@pytest.fixture
def admin_a(make_user, school_a):
    return make_user("admin_a", Role.ADMIN, school_a, email="admin@alpha.test")


@pytest.fixture
def admin_b(make_user, school_b):
    return make_user("admin_b", Role.ADMIN, school_b)

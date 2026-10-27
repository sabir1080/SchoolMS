import pytest
from django.db import IntegrityError

from apps.accounts.models import Role, User

from .conftest import PASSWORD


def login(api, username, password=PASSWORD):
    return api.post("/api/auth/login/", {"username": username, "password": password}, format="json")


def test_health_is_public(api, db):
    assert api.get("/api/health/").json() == {"status": "ok"}


def test_login_with_username_returns_tokens_and_profile(api, admin_a):
    res = login(api, "admin_a")
    assert res.status_code == 200
    body = res.json()
    assert {"access", "refresh"} <= body.keys()
    assert body["user"]["role"] == Role.ADMIN
    assert body["user"]["tenant"]["slug"] == "alpha"


def test_login_with_email_is_case_insensitive(api, admin_a):
    assert login(api, "ADMIN@alpha.test").status_code == 200


def test_login_rejects_wrong_password(api, admin_a):
    assert login(api, "admin_a", "nope").status_code == 401


def test_suspended_tenant_cannot_log_in_or_use_existing_token(api, admin_a, school_a):
    token = login(api, "admin_a").json()["access"]
    school_a.is_active = False
    school_a.save()

    assert login(api, "admin_a").status_code == 401
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    assert api.get("/api/auth/me/").status_code == 401


def test_me_requires_authentication(api, db):
    assert api.get("/api/auth/me/").status_code == 401


def test_super_admin_has_no_tenant(super_admin):
    assert super_admin.role == Role.SUPER_ADMIN
    assert super_admin.tenant is None


@pytest.mark.django_db
def test_non_super_admin_must_belong_to_a_tenant():
    with pytest.raises(IntegrityError):
        User.objects.create_user(username="orphan", password=PASSWORD, role=Role.TEACHER)

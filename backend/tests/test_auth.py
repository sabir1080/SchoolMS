import pytest
from django.db import IntegrityError

from apps.accounts.models import Role, User

from .conftest import PASSWORD


def login(api, code, username, password=PASSWORD):
    return api.post(
        "/api/auth/login/", {"institute_code": code, "username": username, "password": password}, format="json"
    )


def test_health_is_public(api, db):
    assert api.get("/api/health/").json() == {"status": "ok"}


def test_institute_lookup_shows_name(api, school_a):
    res = api.get("/api/public/institutes/ALPHA/")
    assert res.status_code == 200
    assert res.json() == {"name": "Alpha", "slug": "alpha", "institute_type": "school"}


def test_institute_lookup_unknown_and_suspended(api, school_a):
    assert api.get("/api/public/institutes/nope/").status_code == 404
    school_a.is_active = False
    school_a.save()
    assert api.get("/api/public/institutes/alpha/").status_code == 403


def test_login_with_code_and_username(api, admin_a):
    res = login(api, "alpha", "admin_a")
    assert res.status_code == 200
    body = res.json()
    assert {"access", "refresh"} <= body.keys()
    assert body["user"]["role"] == Role.ADMIN
    assert body["user"]["tenant"]["slug"] == "alpha"


def test_login_code_is_case_insensitive_and_email_works(api, admin_a):
    assert login(api, " Alpha ", "ADMIN@alpha.test").status_code == 200


def test_login_rejects_wrong_password_and_unknown_code(api, admin_a):
    assert login(api, "alpha", "admin_a", "nope").status_code == 401
    res = login(api, "zzz", "admin_a")
    assert res.status_code == 401
    assert res.json()["detail"] == "Institute code not found."


def test_user_cannot_log_in_through_another_institute(api, admin_a, school_b):
    assert login(api, "beta", "admin_a").status_code == 401


def test_same_username_in_two_institutes(api, make_user, school_a, school_b):
    make_user("ali", Role.TEACHER, school_a)
    make_user("ali", Role.STUDENT, school_b)
    assert login(api, "alpha", "ali").json()["user"]["role"] == Role.TEACHER
    assert login(api, "beta", "ali").json()["user"]["role"] == Role.STUDENT


def test_username_unique_inside_institute(make_user, school_a):
    make_user("ali", Role.TEACHER, school_a)
    with pytest.raises(IntegrityError):
        make_user("ali", Role.STUDENT, school_a)


def test_inactive_user_cannot_log_in(api, make_user, school_a):
    make_user("gone", Role.TEACHER, school_a, is_active=False)
    assert login(api, "alpha", "gone").status_code == 401


def test_suspended_tenant_cannot_log_in_or_use_existing_token(api, admin_a, school_a):
    token = login(api, "alpha", "admin_a").json()["access"]
    school_a.is_active = False
    school_a.save()

    res = login(api, "alpha", "admin_a")
    assert res.status_code == 401
    assert "suspended" in res.json()["detail"]
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    assert api.get("/api/auth/me/").status_code == 401


def test_platform_login_only_for_super_admin(api, super_admin, admin_a):
    res = api.post("/api/auth/platform-login/", {"username": "owner", "password": PASSWORD}, format="json")
    assert res.status_code == 200
    assert res.json()["user"]["role"] == Role.SUPER_ADMIN
    res = api.post("/api/auth/platform-login/", {"username": "admin_a", "password": PASSWORD}, format="json")
    assert res.status_code == 401


def test_super_admin_cannot_use_institute_login(api, super_admin, school_a):
    assert login(api, "alpha", "owner").status_code == 401


def test_refresh_and_me(api, admin_a):
    tokens = login(api, "alpha", "admin_a").json()
    res = api.post("/api/auth/refresh/", {"refresh": tokens["refresh"]}, format="json")
    assert res.status_code == 200
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {res.json()['access']}")
    assert api.get("/api/auth/me/").json()["username"] == "admin_a"


def test_me_requires_authentication(api, db):
    assert api.get("/api/auth/me/").status_code == 401


def test_super_admin_has_no_tenant(super_admin):
    assert super_admin.role == Role.SUPER_ADMIN
    assert super_admin.tenant is None


@pytest.mark.django_db
def test_non_super_admin_must_belong_to_a_tenant():
    with pytest.raises(IntegrityError):
        User.objects.create_user(username="orphan", password=PASSWORD, role=Role.TEACHER)


def test_login_is_rate_limited(api, admin_a, monkeypatch):
    from rest_framework.throttling import ScopedRateThrottle

    monkeypatch.setattr(ScopedRateThrottle, "THROTTLE_RATES", {"login": "3/min"})
    codes = [login(api, "alpha", "admin_a", "bad").status_code for _ in range(4)]
    assert codes == [401, 401, 401, 429]

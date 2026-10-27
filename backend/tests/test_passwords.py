import pytest

from apps.accounts.models import Role
from apps.accounts.passwords import PasswordPolicy, password_errors

from .conftest import PASSWORD


def auth(api, user):
    api.force_authenticate(user)
    return api


def login(api, code, username, password):
    return api.post(
        "/api/auth/login/", {"institute_code": code, "username": username, "password": password}, format="json"
    )


# --- Policy rules ------------------------------------------------------------

@pytest.mark.parametrize(
    "policy,password,ok",
    [
        ("easy", "1234", True),
        ("easy", "abc", False),
        ("standard", "ali12345", True),
        ("standard", "12345678", False),  # too common
        ("standard", "abc1234", False),  # too short
        ("strong", "Qalam2026x", True),
        ("strong", "qalamkitab", False),  # no number
        ("strong", "password1", False),  # common
    ],
)
def test_policy_rules(policy, password, ok):
    assert (password_errors(password, policy) == []) is ok


def test_new_institutes_default_to_easy(school_a):
    assert school_a.password_policy == PasswordPolicy.EASY


def test_easy_policy_allows_simple_passwords_for_new_users(api, admin_a):
    res = auth(api, admin_a).post("/api/users/", {"username": "kid", "password": "1234", "role": "student"}, format="json")
    assert res.status_code == 201, res.json()
    assert login(api, "alpha", "kid", "1234").status_code == 200


def test_strong_policy_is_enforced_for_new_users(api, admin_a, school_a):
    school_a.password_policy = PasswordPolicy.STRONG
    school_a.save()
    api = auth(api, admin_a)
    res = api.post("/api/users/", {"username": "kid", "password": "1234", "role": "student"}, format="json")
    assert res.status_code == 400
    assert any("at least 8" in m for m in res.json()["password"])
    res = api.post("/api/users/", {"username": "kid", "password": "Qalam2026x", "role": "student"}, format="json")
    assert res.status_code == 201


# --- Change own password -------------------------------------------------------

def test_user_changes_own_password(api, make_user, school_a):
    teacher = make_user("t1", Role.TEACHER, school_a)
    res = auth(api, teacher).post(
        "/api/auth/change-password/", {"current_password": PASSWORD, "new_password": "abcd"}, format="json"
    )
    assert res.status_code == 200, res.json()
    api.force_authenticate(None)
    assert login(api, "alpha", "t1", "abcd").status_code == 200
    assert login(api, "alpha", "t1", PASSWORD).status_code == 401


def test_change_password_requires_correct_current_password(api, admin_a):
    res = auth(api, admin_a).post(
        "/api/auth/change-password/", {"current_password": "wrong", "new_password": "abcd"}, format="json"
    )
    assert res.status_code == 400
    assert "current_password" in res.json()


def test_change_password_follows_institute_policy(api, admin_a, school_a):
    school_a.password_policy = PasswordPolicy.STANDARD
    school_a.save()
    res = auth(api, admin_a).post(
        "/api/auth/change-password/", {"current_password": PASSWORD, "new_password": "abcd"}, format="json"
    )
    assert res.status_code == 400
    assert "new_password" in res.json()


def test_change_password_works_when_subscription_expired(api, admin_a, school_a):
    from datetime import timedelta

    from django.utils import timezone

    sub = school_a.subscription
    sub.current_period_end = timezone.now() - timedelta(days=1)
    sub.save()
    res = auth(api, admin_a).post(
        "/api/auth/change-password/", {"current_password": PASSWORD, "new_password": "abcd"}, format="json"
    )
    assert res.status_code == 200


def test_super_admin_password_uses_platform_policy(api, super_admin):
    api = auth(api, super_admin)
    res = api.post("/api/auth/change-password/", {"current_password": PASSWORD, "new_password": "abcd"}, format="json")
    assert res.status_code == 400  # platform default is "standard"
    res = api.post(
        "/api/auth/change-password/", {"current_password": PASSWORD, "new_password": "Owner-new-55"}, format="json"
    )
    assert res.status_code == 200
    api.force_authenticate(None)
    res = api.post("/api/auth/platform-login/", {"username": "owner", "password": "Owner-new-55"}, format="json")
    assert res.status_code == 200


# --- Admin resets ------------------------------------------------------------

def test_admin_resets_user_password(api, admin_a, make_user, school_a):
    teacher = make_user("t1", Role.TEACHER, school_a)
    res = auth(api, admin_a).post(f"/api/users/{teacher.pk}/set-password/", {"new_password": "9999"}, format="json")
    assert res.status_code == 200
    api.force_authenticate(None)
    assert login(api, "alpha", "t1", "9999").status_code == 200


def test_admin_cannot_reset_password_in_other_institute(api, admin_a, admin_b):
    res = auth(api, admin_a).post(f"/api/users/{admin_b.pk}/set-password/", {"new_password": "9999"}, format="json")
    assert res.status_code == 404


def test_teacher_cannot_reset_passwords(api, make_user, school_a):
    teacher = make_user("t1", Role.TEACHER, school_a)
    other = make_user("t2", Role.TEACHER, school_a)
    res = auth(api, teacher).post(f"/api/users/{other.pk}/set-password/", {"new_password": "9999"}, format="json")
    assert res.status_code == 403


def test_super_admin_resets_institute_admin_password(api, super_admin, admin_a, school_a, make_user):
    make_user("t1", Role.TEACHER, school_a)
    api = auth(api, super_admin)
    url = f"/api/platform/tenants/{school_a.pk}/reset-admin-password/"
    assert api.post(url, {"username": "admin_a", "new_password": "4321"}, format="json").status_code == 200
    # Only admins can be reset from the platform.
    assert api.post(url, {"username": "t1", "new_password": "4321"}, format="json").status_code == 404
    api.force_authenticate(None)
    assert login(api, "alpha", "admin_a", "4321").status_code == 200


def test_platform_tenant_list_shows_admin_usernames(api, super_admin, admin_a, school_a):
    res = auth(api, super_admin).get("/api/platform/tenants/")
    row = next(t for t in res.json()["results"] if t["slug"] == "alpha")
    assert row["admin_usernames"] == ["admin_a"]
    assert row["password_policy"] == "easy"


# --- Institute settings --------------------------------------------------------

def test_admin_views_and_changes_institute_settings(api, admin_a, school_a):
    api = auth(api, admin_a)
    res = api.get("/api/institute/settings/")
    assert res.status_code == 200
    assert res.json()["password_policy"] == "easy"
    res = api.patch(
        "/api/institute/settings/",
        {"password_policy": "strong", "phone": "0300-1234567", "slug": "hacked", "currency": "USD"},
        format="json",
    )
    assert res.status_code == 200
    school_a.refresh_from_db()
    assert school_a.password_policy == "strong"
    assert school_a.phone == "0300-1234567"
    assert school_a.slug == "alpha"  # read-only
    assert school_a.currency == "PKR"  # read-only


def test_only_admins_change_institute_settings(api, make_user, school_a):
    teacher = make_user("t1", Role.TEACHER, school_a)
    assert auth(api, teacher).patch("/api/institute/settings/", {"password_policy": "easy"}, format="json").status_code == 403


def test_me_includes_password_policy(api, admin_a):
    assert auth(api, admin_a).get("/api/auth/me/").json()["tenant"]["password_policy"] == "easy"

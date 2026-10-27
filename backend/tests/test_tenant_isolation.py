from apps.accounts.models import Role, User


def auth(api, user):
    api.force_authenticate(user)
    return api


def test_admin_only_sees_users_of_own_institute(api, admin_a, admin_b, make_user, school_b):
    make_user("teacher_b", Role.TEACHER, school_b)
    res = auth(api, admin_a).get("/api/users/")
    assert res.status_code == 200
    assert [u["username"] for u in res.json()["results"]] == ["admin_a"]


def test_admin_cannot_open_user_of_other_institute(api, admin_a, admin_b):
    assert auth(api, admin_a).get(f"/api/users/{admin_b.pk}/").status_code == 404


def test_admin_creates_user_inside_own_institute(api, admin_a, school_a, school_b):
    res = auth(api, admin_a).post(
        "/api/users/",
        # A tenant in the payload must be ignored.
        {"username": "t1", "password": "Str0ng-pass-123", "role": "teacher", "tenant": school_b.pk},
        format="json",
    )
    assert res.status_code == 201, res.json()
    assert User.objects.get(username="t1").tenant == school_a


def test_admin_cannot_create_super_admin(api, admin_a):
    res = auth(api, admin_a).post(
        "/api/users/", {"username": "x", "password": "Str0ng-pass-123", "role": "super_admin"}, format="json"
    )
    assert res.status_code == 400


def test_too_short_password_is_rejected(api, admin_a):
    res = auth(api, admin_a).post("/api/users/", {"username": "x", "password": "123", "role": "student"}, format="json")
    assert res.status_code == 400
    assert "password" in res.json()


def test_delete_deactivates_instead_of_removing(api, admin_a, make_user, school_a):
    teacher = make_user("t2", Role.TEACHER, school_a)
    assert auth(api, admin_a).delete(f"/api/users/{teacher.pk}/").status_code == 204
    teacher.refresh_from_db()
    assert teacher.is_active is False


def test_teacher_cannot_manage_users(api, make_user, school_a):
    teacher = make_user("t3", Role.TEACHER, school_a)
    assert auth(api, teacher).get("/api/users/").status_code == 403


def test_super_admin_creates_institute_with_first_admin(api, super_admin):
    res = auth(api, super_admin).post(
        "/api/platform/tenants/",
        {
            "name": "City Coaching",
            "slug": "city-coaching",
            "institute_type": "coaching",
            "country": "AE",
            "currency": "AED",
            "timezone": "Asia/Dubai",
            "admin_username": "city_admin",
            "admin_email": "Admin@City.test",
            "admin_password": "Str0ng-pass-123",
        },
        format="json",
    )
    assert res.status_code == 201, res.json()
    admin = User.objects.get(username="city_admin")
    assert admin.role == Role.ADMIN
    assert admin.tenant.slug == "city-coaching"
    assert admin.email == "admin@city.test"
    assert "admin_password" not in res.json()
    assert res.json()["subscription"]["status"] == "trialing"


def test_same_username_allowed_in_other_institute_but_not_own(api, admin_a, make_user, school_b):
    make_user("ali", Role.TEACHER, school_b)
    api = auth(api, admin_a)
    payload = {"username": "ali", "password": "Str0ng-pass-123", "role": "teacher"}
    assert api.post("/api/users/", payload, format="json").status_code == 201
    res = api.post("/api/users/", payload, format="json")
    assert res.status_code == 400
    assert "username" in res.json()


def test_institute_admin_cannot_access_platform_api(api, admin_a):
    assert auth(api, admin_a).get("/api/platform/tenants/").status_code == 403

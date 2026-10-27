from apps.accounts.models import Role

PNG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="


def auth(api, user):
    api.force_authenticate(user)
    return api


def test_admin_sets_logo_and_colour(api, admin_a, school_a):
    api = auth(api, admin_a)
    res = api.patch("/api/institute/settings/", {"logo": PNG, "brand_color": "teal"}, format="json")
    assert res.status_code == 200, res.json()
    assert res.json()["brand"] == {"logo": PNG, "color": "teal", "hex": "#0f766e", "allowed": True}
    assert api.get("/api/auth/me/").json()["tenant"]["brand"]["color"] == "teal"
    api.force_authenticate(None)
    public = api.get("/api/public/institutes/alpha/").json()
    assert public["brand"]["logo"] == PNG and public["brand"]["hex"] == "#0f766e"
    # removing the logo
    assert auth(api, admin_a).patch("/api/institute/settings/", {"logo": ""}, format="json").json()["brand"]["logo"] == ""


def test_branding_validation(api, admin_a):
    api = auth(api, admin_a)
    assert api.patch("/api/institute/settings/", {"brand_color": "neon"}, format="json").status_code == 400
    assert api.patch("/api/institute/settings/", {"logo": "data:text/html;base64,PGgxPg=="}, format="json").status_code == 400
    assert api.patch("/api/institute/settings/", {"logo": "data:image/png;base64," + "A" * 200_001}, format="json").status_code == 400


def test_branding_needs_plan_feature(api, admin_a, make_user, school_a):
    api = auth(api, admin_a)
    api.patch("/api/institute/settings/", {"logo": PNG, "brand_color": "rose"}, format="json")
    plan = school_a.subscription.plan
    plan.features = [f for f in plan.features if f != "white_label"]
    plan.save()
    res = api.patch("/api/institute/settings/", {"brand_color": "teal"}, format="json")
    assert res.status_code == 400 and "Upgrade" in str(res.json())
    # the saved branding is hidden while the plan does not include it
    brand = api.get("/api/auth/me/").json()["tenant"]["brand"]
    assert brand == {"logo": "", "color": "indigo", "hex": "#4f46e5", "allowed": False}
    # other settings still save
    assert api.patch("/api/institute/settings/", {"phone": "042-1234567"}, format="json").status_code == 200
    assert auth(api, make_user("t", Role.TEACHER, school_a)).patch("/api/institute/settings/", {"brand_color": "teal"}, format="json").status_code == 403

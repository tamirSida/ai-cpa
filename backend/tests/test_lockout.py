"""App-wide lockout: pending/disabled users are blocked everywhere, including
onboarding (POST /businesses, GET /businesses/me) and every business-scoped
route via get_owned_business. The account_pending/account_disabled 403 must
fire BEFORE the ownership 'forbidden' 403."""

CREATE_BODY = {
    "businessName": "עיצובים של נועה", "ownerName": "נועה לוי",
    "businessIdNumber": "123456789", "address": "הרצל 1, תל אביב",
    "phone": "050-1234567", "email": "noa@example.com",
}


def _set_status(db, status: str, uid: str = "test-uid") -> None:
    db.collection("users").document(uid).update({"status": status})


# --- pending user blocked from onboarding -----------------------------------

def test_pending_blocked_get_me(api, db):
    _set_status(db, "pending")
    r = api.get("/api/businesses/me")
    assert r.status_code == 403 and r.json()["detail"]["code"] == "account_pending"


def test_pending_blocked_create_business(api, db):
    _set_status(db, "pending")
    r = api.post("/api/businesses", json=CREATE_BODY)
    assert r.status_code == 403 and r.json()["detail"]["code"] == "account_pending"


# --- disabled user blocked from onboarding ----------------------------------

def test_disabled_blocked_get_me(api, db):
    _set_status(db, "disabled")
    r = api.get("/api/businesses/me")
    assert r.status_code == 403 and r.json()["detail"]["code"] == "account_disabled"


def test_disabled_blocked_create_business(api, db):
    _set_status(db, "disabled")
    r = api.post("/api/businesses", json=CREATE_BODY)
    assert r.status_code == 403 and r.json()["detail"]["code"] == "account_disabled"


# --- transitive gate on a business-scoped route -----------------------------

def test_pending_blocked_from_business_scoped_route(api, db, make_business):
    biz = make_business()  # owned by test-uid
    _set_status(db, "pending")
    r = api.get(f"/api/businesses/{biz['id']}/expenses")
    assert r.status_code == 403 and r.json()["detail"]["code"] == "account_pending"


def test_disabled_blocked_from_business_scoped_route(api, db, make_business):
    biz = make_business()
    _set_status(db, "disabled")
    r = api.get(f"/api/businesses/{biz['id']}/expenses")
    assert r.status_code == 403 and r.json()["detail"]["code"] == "account_disabled"


# --- active user unaffected --------------------------------------------------

def test_active_get_me_404_when_no_business(api):
    r = api.get("/api/businesses/me")
    assert r.status_code == 404 and r.json()["detail"]["code"] == "business_not_found"


def test_active_get_me_200_with_business(api):
    api.post("/api/businesses", json=CREATE_BODY)
    r = api.get("/api/businesses/me")
    assert r.status_code == 200 and r.json()["ownerUserId"] == "test-uid"


def test_active_business_scoped_route_ok(api, make_business):
    biz = make_business()
    r = api.get(f"/api/businesses/{biz['id']}/expenses")
    assert r.status_code == 200 and r.json() == []


# --- foreign business still forbidden (NOT account_pending) ------------------

def test_active_foreign_business_forbidden(api, make_business):
    other = make_business(ownerUserId="someone-else")
    r = api.get(f"/api/businesses/{other['id']}/expenses")
    assert r.status_code == 403 and r.json()["detail"]["code"] == "forbidden"

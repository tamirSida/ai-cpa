"""Admin user-management endpoints: list/detail/approve/enable/disable/role/budget."""


# --- authz: non-admin forbidden --------------------------------------------

def test_non_admin_forbidden_list(api):
    r = api.get("/api/admin/users")
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "forbidden_not_admin"


def test_non_admin_forbidden_action(api):
    r = api.post("/api/admin/users/some-uid/enable")
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "forbidden_not_admin"


# --- list + filter ----------------------------------------------------------

def test_list_all_users(admin_api, make_user):
    make_user(uid="u1", email="alice@x.com", status="active")
    make_user(uid="u2", email="bob@x.com", status="pending")
    r = admin_api.get("/api/admin/users")
    assert r.status_code == 200
    uids = {u["uid"] for u in r.json()}
    # admin-uid is seeded by the admin_api fixture and must be included.
    assert {"u1", "u2", "admin-uid"} <= uids


def test_list_status_filter(admin_api, make_user):
    make_user(uid="u1", email="alice@x.com", status="active")
    make_user(uid="p1", email="pend@x.com", status="pending")
    make_user(uid="p2", email="pend2@x.com", status="pending")
    r = admin_api.get("/api/admin/users", params={"status": "pending"})
    assert r.status_code == 200
    statuses = {u["status"] for u in r.json()}
    uids = {u["uid"] for u in r.json()}
    assert statuses == {"pending"}
    assert uids == {"p1", "p2"}


def test_list_q_substring_case_insensitive(admin_api, make_user):
    make_user(uid="u1", email="Noa@x.com", status="active")
    make_user(uid="u2", email="bob@x.com", status="active")
    r = admin_api.get("/api/admin/users", params={"q": "noa"})
    assert r.status_code == 200
    uids = {u["uid"] for u in r.json()}
    assert uids == {"u1"}


# --- detail -----------------------------------------------------------------

def test_detail_with_business(admin_api, make_user, make_business, freeze_month):
    make_user(uid="u1", email="u1@x.com")
    make_business(ownerUserId="u1", businessName="עסק של יו1")
    r = admin_api.get("/api/admin/users/u1")
    assert r.status_code == 200
    body = r.json()
    assert body["uid"] == "u1"
    assert body["usage"]["aiCostUsd"] == 0
    assert body["business"]["businessName"] == "עסק של יו1"
    assert body["business"]["businessIdNumber"] == "123456789"


def test_detail_without_business(admin_api, make_user, freeze_month):
    make_user(uid="u1", email="u1@x.com")
    r = admin_api.get("/api/admin/users/u1")
    assert r.status_code == 200
    assert r.json()["business"] is None


def test_detail_unknown_404(admin_api):
    r = admin_api.get("/api/admin/users/nope")
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "user_not_found"


# --- approve ----------------------------------------------------------------

def test_approve_unlimited(admin_api, db, make_user):
    make_user(uid="p1", email="p1@x.com", status="pending")
    r = admin_api.post("/api/admin/users/p1/approve", json={"aiBudgetUsd": None})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "active"
    assert body["aiBudgetUsd"] is None
    assert body["approvedByUid"] == "admin-uid"
    assert body["approvedAt"] is not None
    raw = db.collection("users").document("p1").get().to_dict()
    assert raw["status"] == "active"
    assert "aiBudgetUsd" in raw and raw["aiBudgetUsd"] is None
    assert raw["approvedByUid"] == "admin-uid"


def test_approve_default_budget(admin_api, make_user):
    make_user(uid="p1", email="p1@x.com", status="pending")
    r = admin_api.post("/api/admin/users/p1/approve", json={})
    assert r.status_code == 200
    assert r.json()["aiBudgetUsd"] == 3.0


def test_approve_explicit_number(admin_api, make_user):
    make_user(uid="p1", email="p1@x.com", status="pending")
    r = admin_api.post("/api/admin/users/p1/approve", json={"aiBudgetUsd": 5})
    assert r.status_code == 200
    assert r.json()["aiBudgetUsd"] == 5.0


def test_approve_non_pending_conflict(admin_api, make_user):
    make_user(uid="u1", email="u1@x.com", status="active")
    r = admin_api.post("/api/admin/users/u1/approve", json={"aiBudgetUsd": 5})
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "invalid_user_status"


def test_approve_unknown_404(admin_api):
    r = admin_api.post("/api/admin/users/nope/approve", json={})
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "user_not_found"


# --- enable / disable -------------------------------------------------------

def test_disable_then_enable(admin_api, db, make_user):
    make_user(uid="u1", email="u1@x.com", status="active")
    r = admin_api.post("/api/admin/users/u1/disable")
    assert r.status_code == 200
    assert r.json()["status"] == "disabled"
    r = admin_api.post("/api/admin/users/u1/enable")
    assert r.status_code == 200
    assert r.json()["status"] == "active"
    assert db.collection("users").document("u1").get().to_dict()["status"] == "active"


def test_disable_self_conflict(admin_api):
    r = admin_api.post("/api/admin/users/admin-uid/disable")
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "cannot_disable_self"


def test_disable_unknown_404(admin_api):
    r = admin_api.post("/api/admin/users/nope/disable")
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "user_not_found"


# --- role -------------------------------------------------------------------

def test_change_role(admin_api, db, make_user):
    make_user(uid="u1", email="u1@x.com", role="user")
    r = admin_api.post("/api/admin/users/u1/role", json={"role": "admin"})
    assert r.status_code == 200
    assert r.json()["role"] == "admin"
    assert db.collection("users").document("u1").get().to_dict()["role"] == "admin"


def test_change_own_role_conflict(admin_api):
    r = admin_api.post("/api/admin/users/admin-uid/role", json={"role": "user"})
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "cannot_change_own_role"


# --- budget -----------------------------------------------------------------

def test_set_budget_number_then_unlimited(admin_api, db, make_user):
    make_user(uid="u1", email="u1@x.com")
    r = admin_api.post("/api/admin/users/u1/budget", json={"aiBudgetUsd": 7.5})
    assert r.status_code == 200
    assert r.json()["aiBudgetUsd"] == 7.5
    assert db.collection("users").document("u1").get().to_dict()["aiBudgetUsd"] == 7.5

    r = admin_api.post("/api/admin/users/u1/budget", json={"aiBudgetUsd": None})
    assert r.status_code == 200
    assert r.json()["aiBudgetUsd"] is None
    raw = db.collection("users").document("u1").get().to_dict()
    assert "aiBudgetUsd" in raw and raw["aiBudgetUsd"] is None


def test_set_budget_unknown_404(admin_api):
    r = admin_api.post("/api/admin/users/nope/budget", json={"aiBudgetUsd": 1})
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "user_not_found"


# --- budget hardening: reject non-finite / negative -------------------------

def test_budget_negative_rejected(admin_api, make_user):
    make_user(uid="u1", email="u1@x.com")
    r = admin_api.post("/api/admin/users/u1/budget", json={"aiBudgetUsd": -1})
    assert r.status_code == 422


def test_budget_nan_rejected(admin_api, make_user):
    # Python json.dumps emits bare NaN (invalid JSON but accepted by many parsers);
    # post a raw body so the float reaches validation as NaN.
    make_user(uid="u1", email="u1@x.com")
    r = admin_api.post(
        "/api/admin/users/u1/budget",
        content=b'{"aiBudgetUsd": NaN}',
        headers={"content-type": "application/json"},
    )
    assert r.status_code == 422


def test_budget_infinity_rejected(admin_api, make_user):
    make_user(uid="u1", email="u1@x.com")
    r = admin_api.post(
        "/api/admin/users/u1/budget",
        content=b'{"aiBudgetUsd": Infinity}',
        headers={"content-type": "application/json"},
    )
    assert r.status_code == 422


def test_budget_null_still_unlimited(admin_api, db, make_user):
    make_user(uid="u1", email="u1@x.com")
    r = admin_api.post("/api/admin/users/u1/budget", json={"aiBudgetUsd": None})
    assert r.status_code == 200
    assert r.json()["aiBudgetUsd"] is None


def test_budget_zero_allowed(admin_api, db, make_user):
    make_user(uid="u1", email="u1@x.com")
    r = admin_api.post("/api/admin/users/u1/budget", json={"aiBudgetUsd": 0})
    assert r.status_code == 200
    assert r.json()["aiBudgetUsd"] == 0


def test_approve_negative_rejected(admin_api, make_user):
    make_user(uid="p1", email="p1@x.com", status="pending")
    r = admin_api.post("/api/admin/users/p1/approve", json={"aiBudgetUsd": -1})
    assert r.status_code == 422


def test_approve_nan_rejected(admin_api, make_user):
    make_user(uid="p1", email="p1@x.com", status="pending")
    r = admin_api.post(
        "/api/admin/users/p1/approve",
        content=b'{"aiBudgetUsd": NaN}',
        headers={"content-type": "application/json"},
    )
    assert r.status_code == 422


def test_approve_infinity_rejected(admin_api, make_user):
    make_user(uid="p1", email="p1@x.com", status="pending")
    r = admin_api.post(
        "/api/admin/users/p1/approve",
        content=b'{"aiBudgetUsd": Infinity}',
        headers={"content-type": "application/json"},
    )
    assert r.status_code == 422


def test_approve_null_still_unlimited(admin_api, make_user):
    make_user(uid="p1", email="p1@x.com", status="pending")
    r = admin_api.post("/api/admin/users/p1/approve", json={"aiBudgetUsd": None})
    assert r.status_code == 200
    assert r.json()["aiBudgetUsd"] is None


def test_approve_zero_allowed(admin_api, make_user):
    make_user(uid="p1", email="p1@x.com", status="pending")
    r = admin_api.post("/api/admin/users/p1/approve", json={"aiBudgetUsd": 0})
    assert r.status_code == 200
    assert r.json()["aiBudgetUsd"] == 0

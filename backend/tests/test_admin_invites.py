from datetime import datetime, timezone

from app.core.config import Settings
from app.services import user_service


def _settings(**overrides) -> Settings:
    # _env_file=None: hermetic, ignore developer .env. No bootstrap admins by default.
    base = {"bootstrap_admin_emails": [], "default_ai_budget_usd": 3.0}
    base.update(overrides)
    return Settings(_env_file=None, **base)


# --- authz: non-admin forbidden --------------------------------------------

def test_non_admin_forbidden_list(api):
    r = api.get("/api/admin/invites")
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "forbidden_not_admin"


def test_non_admin_forbidden_create(api):
    r = api.post("/api/admin/invites", json={"email": "x@y.com"})
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "forbidden_not_admin"


def test_non_admin_forbidden_revoke(api):
    r = api.delete("/api/admin/invites/x@y.com")
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "forbidden_not_admin"


# --- create + normalize -----------------------------------------------------

def test_create_normalizes_email(admin_api, db):
    r = admin_api.post("/api/admin/invites", json={"email": "  New@X.com "})
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "new@x.com"
    assert body["id"] == "new@x.com"
    assert body["status"] == "pending"
    assert body["invitedByUid"] == "admin-uid"
    raw = db.collection("invites").document("new@x.com").get().to_dict()
    assert raw is not None
    assert raw["email"] == "new@x.com"
    assert raw["status"] == "pending"
    assert raw["invitedByUid"] == "admin-uid"


def test_create_idempotent_reinvite(admin_api, db):
    admin_api.post("/api/admin/invites", json={"email": "dup@x.com"})
    r = admin_api.post("/api/admin/invites", json={"email": "DUP@x.com"})
    assert r.status_code == 201
    assert r.json()["status"] == "pending"
    docs = list(db.collection("invites").stream())
    emails = [d.id for d in docs]
    assert emails.count("dup@x.com") == 1
    assert len(docs) == 1


def test_create_already_a_user(admin_api, make_user):
    make_user(uid="u9", email="taken@x.com")
    r = admin_api.post("/api/admin/invites", json={"email": "taken@x.com"})
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "user_already_exists"


# --- email validation before doc-id use -------------------------------------

def test_create_email_with_slash_rejected(admin_api):
    r = admin_api.post("/api/admin/invites", json={"email": "a/b@x.com"})
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "invalid_email"


def test_create_non_email_rejected(admin_api):
    r = admin_api.post("/api/admin/invites", json={"email": "notanemail"})
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "invalid_email"


def test_create_blank_email_rejected(admin_api):
    r = admin_api.post("/api/admin/invites", json={"email": "   "})
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "invalid_email"


# --- list -------------------------------------------------------------------

def test_list_invites(admin_api):
    admin_api.post("/api/admin/invites", json={"email": "a@x.com"})
    admin_api.post("/api/admin/invites", json={"email": "b@x.com"})
    r = admin_api.get("/api/admin/invites")
    assert r.status_code == 200
    emails = {inv["email"] for inv in r.json()}
    assert emails == {"a@x.com", "b@x.com"}


def test_list_invites_status_filter(admin_api, db):
    admin_api.post("/api/admin/invites", json={"email": "a@x.com"})
    admin_api.post("/api/admin/invites", json={"email": "b@x.com"})
    admin_api.delete("/api/admin/invites/b@x.com")  # b -> revoked
    r = admin_api.get("/api/admin/invites", params={"status": "pending"})
    assert r.status_code == 200
    emails = {inv["email"] for inv in r.json()}
    assert emails == {"a@x.com"}


# --- revoke -----------------------------------------------------------------

def test_revoke_pending(admin_api, db):
    admin_api.post("/api/admin/invites", json={"email": "new@x.com"})
    r = admin_api.delete("/api/admin/invites/new@x.com")
    assert r.status_code == 200
    assert r.json() == {"status": "revoked"}
    raw = db.collection("invites").document("new@x.com").get().to_dict()
    assert raw["status"] == "revoked"


def test_revoke_accepted_conflict(admin_api, db):
    now = datetime.now(timezone.utc)
    db.collection("invites").document("acc@x.com").set(
        {"email": "acc@x.com", "status": "accepted", "invitedByUid": "admin-uid",
         "acceptedByUid": "u1", "createdAt": now, "updatedAt": now}
    )
    r = admin_api.delete("/api/admin/invites/acc@x.com")
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "invite_not_revocable"


def test_revoke_absent_404(admin_api):
    r = admin_api.delete("/api/admin/invites/nope@x.com")
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "invite_not_found"


# --- e2e: invite -> ensure_user activates -----------------------------------

def test_invite_then_ensure_user_activates(admin_api, db):
    admin_api.post("/api/admin/invites", json={"email": "join@x.com"})
    user = user_service.ensure_user(
        db, uid="newbie", email="join@x.com", name="N", settings=_settings()
    )
    assert user.status == "active"
    assert user.invited_by_uid == "admin-uid"
    invite = db.collection("invites").document("join@x.com").get().to_dict()
    assert invite["status"] == "accepted"
    assert invite["acceptedByUid"] == "newbie"

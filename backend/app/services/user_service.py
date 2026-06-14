from google.cloud import firestore

from app.core.errors import api_error
from app.schemas.user import User
from app.utils.dates import now_il


def ensure_user(db: firestore.Client, *, uid: str, email: str | None, name: str | None, settings) -> User:
    """Idempotent-on-uid: lazily create users/{uid} on first sign-in with the
    correct role/status, applying bootstrap-admin > pending-invite > pending
    precedence. Returns the existing doc unchanged if already present."""
    ref = db.collection("users").document(uid)
    snap = ref.get()
    if snap.exists:
        return User.model_validate(snap.to_dict())

    if email is None:
        api_error(400, "email_required", "Sign-in token has no email")

    email = email.strip().lower()
    now = now_il()
    data: dict = {
        "uid": uid,
        "email": email,
        "displayName": name,
        "role": "user",
        "status": "pending",
        "createdAt": now,
        "updatedAt": now,
    }

    bootstrap = {e.strip().lower() for e in settings.bootstrap_admin_emails}
    invite_ref = db.collection("invites").document(email)
    invite_snap = invite_ref.get()
    invite = invite_snap.to_dict() if invite_snap.exists else None

    if email in bootstrap:
        data["role"] = "admin"
        data["status"] = "active"
        data["aiBudgetUsd"] = settings.default_ai_budget_usd
    elif invite is not None and invite.get("status") == "pending":
        data["status"] = "active"
        data["aiBudgetUsd"] = settings.default_ai_budget_usd
        data["invitedByUid"] = invite.get("invitedByUid")
        invite_ref.update({"status": "accepted", "acceptedByUid": uid, "updatedAt": now})
    # else: role="user", status="pending"; aiBudgetUsd stays unset (budget set at approval).

    data = {k: v for k, v in data.items() if v is not None}
    ref.set(data)
    return User.model_validate(data)

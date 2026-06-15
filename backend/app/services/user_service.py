from google.cloud import firestore

from app.core.errors import api_error
from app.schemas.user import User
from app.utils.dates import now_il


def ensure_user(db: firestore.Client, *, uid: str, email: str | None, name: str | None, settings) -> User:
    """Idempotent-on-uid: lazily create users/{uid} on first sign-in with the
    correct role/status, applying bootstrap-admin > pending-invite > pending
    precedence. Returns the existing doc unchanged if already present.

    The create path runs in a TRANSACTION: on first sign-in the frontend fires
    /users/me and /businesses/me concurrently, so two requests can both reach
    ensure_user before the doc exists. Without a transaction, one request could
    consume the invite (status->active, invite->accepted) while the other — now
    reading the invite as already 'accepted' — recreates the user as 'pending'
    and overwrites the active record. The transaction serializes them: the second
    re-reads inside the txn, sees the doc already exists, and returns it unchanged.
    """
    ref = db.collection("users").document(uid)
    snap = ref.get()
    if snap.exists:  # fast path: existing users skip the transaction entirely
        return User.model_validate(snap.to_dict())

    if email is None:
        api_error(400, "email_required", "Sign-in token has no email")
    email = email.strip().lower()
    bootstrap = {e.strip().lower() for e in settings.bootstrap_admin_emails}

    @firestore.transactional
    def _create(tx) -> dict:
        # Re-read inside the txn — a concurrent first-sign-in may have created it.
        existing = ref.get(transaction=tx)
        if existing.exists:
            return existing.to_dict()

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

        invite_ref = db.collection("invites").document(email)
        invite_snap = invite_ref.get(transaction=tx)  # all reads before any writes
        invite = invite_snap.to_dict() if invite_snap.exists else None

        if email in bootstrap:
            data["role"] = "admin"
            data["status"] = "active"
            data["aiBudgetUsd"] = settings.default_ai_budget_usd
        elif invite is not None and invite.get("status") == "pending":
            data["status"] = "active"
            data["aiBudgetUsd"] = settings.default_ai_budget_usd
            data["invitedByUid"] = invite.get("invitedByUid")
            tx.update(invite_ref, {"status": "accepted", "acceptedByUid": uid, "updatedAt": now})
        # else: role="user", status="pending"; aiBudgetUsd stays unset (set at approval).

        data = {k: v for k, v in data.items() if v is not None}
        tx.set(ref, data)
        return data

    return User.model_validate(_create(db.transaction()))

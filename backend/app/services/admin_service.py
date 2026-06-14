from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from app.core.errors import api_error
from app.schemas.invite import Invite
from app.utils.dates import now_il


def _normalize_email(email: str) -> str:
    norm = (email or "").strip().lower()
    if not norm:
        api_error(422, "invalid_email", "Email is required")
    return norm


def _invite_from_snap(snap) -> Invite:
    # id/email both come from the doc id (they are equal by construction).
    data = snap.to_dict() or {}
    return Invite.model_validate({**data, "id": snap.id, "email": snap.id})


def list_invites(db: firestore.Client, status: str | None) -> list[Invite]:
    col = db.collection("invites")
    query = col.where(filter=FieldFilter("status", "==", status)) if status else col
    return [_invite_from_snap(snap) for snap in query.stream()]


def create_invite(db: firestore.Client, admin_uid: str, email: str) -> Invite:
    norm = _normalize_email(email)

    existing_user = list(
        db.collection("users").where(filter=FieldFilter("email", "==", norm)).limit(1).stream()
    )
    if existing_user:
        api_error(409, "user_already_exists", "כבר קיים משתמש עם האימייל הזה")

    now = now_il()
    ref = db.collection("invites").document(norm)
    snap = ref.get()
    # Preserve original createdAt across a re-invite (revoked -> pending reset).
    created_at = snap.to_dict().get("createdAt", now) if snap.exists else now
    data = {
        "email": norm,
        "status": "pending",
        "invitedByUid": admin_uid,
        "createdAt": created_at,
        "updatedAt": now,
    }
    ref.set(data)
    return _invite_from_snap(ref.get())


def revoke_invite(db: firestore.Client, email: str) -> dict:
    norm = _normalize_email(email)
    ref = db.collection("invites").document(norm)
    snap = ref.get()
    if not snap.exists:
        api_error(404, "invite_not_found", "ההזמנה לא נמצאה")
    if snap.to_dict().get("status") == "accepted":
        api_error(409, "invite_not_revocable", "לא ניתן לבטל הזמנה שכבר נוצלה")
    ref.update({"status": "revoked", "updatedAt": now_il()})
    return {"status": "revoked"}

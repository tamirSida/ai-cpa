import re

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from app.core.errors import api_error
from app.schemas.invite import Invite
from app.schemas.user import AdminUserDetail, BusinessSummary, User
from app.services import business_service, usage_service
from app.utils.dates import now_il

# Basic email shape: no '@', whitespace or '/' in any segment; requires a dotted domain.
# '/' must be rejected because the normalized email is used as a Firestore document id.
_EMAIL_RE = re.compile(r"^[^@\s/]+@[^@\s/]+\.[^@\s/]+$")
_MAX_EMAIL_LEN = 320  # RFC 5321 max email length


def _normalize_email(email: str) -> str:
    """Lowercase/trim and validate. The result is used directly as a Firestore
    document id (invites/{email}), so it must be a safe, sane email shape — reject
    empties, control chars, '/' (path separator), over-length, or non-email strings."""
    norm = (email or "").strip().lower()
    if (
        not norm
        or len(norm) > _MAX_EMAIL_LEN
        or any(ord(ch) < 0x20 for ch in norm)  # control chars
        or not _EMAIL_RE.match(norm)
    ):
        api_error(422, "invalid_email", "כתובת אימייל לא תקינה")
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


# --- user management --------------------------------------------------------

def _get_user_or_404(db: firestore.Client, uid: str) -> dict:
    snap = db.collection("users").document(uid).get()
    if not snap.exists:
        api_error(404, "user_not_found", "המשתמש לא נמצא")
    return snap.to_dict()


def list_users(
    db: firestore.Client, status: str | None, q: str | None, limit: int = 50
) -> list[User]:
    limit = min(max(limit, 1), 200)  # cap at 200
    col = db.collection("users")
    query = col.where(filter=FieldFilter("status", "==", status)) if status else col
    users = [User.model_validate(snap.to_dict()) for snap in query.stream()]
    if q:
        needle = q.strip().lower()
        users = [u for u in users if needle in u.email.lower()]
    return users[:limit]


def get_user_detail(db: firestore.Client, uid: str) -> AdminUserDetail:
    user = User.model_validate(_get_user_or_404(db, uid))
    usage = usage_service.usage_summary(db, user)
    biz = business_service.get_business_by_owner(db, uid)
    summary = (
        BusinessSummary(
            id=biz.id,
            business_name=biz.business_name,
            business_id_number=biz.business_id_number,
        )
        if biz is not None
        else None
    )
    return AdminUserDetail(**user.model_dump(), usage=usage, business=summary)


def approve_user(
    db: firestore.Client, admin_uid: str, uid: str, ai_budget_usd: float | None
) -> User:
    data = _get_user_or_404(db, uid)
    if data.get("status") != "pending":
        api_error(409, "invalid_user_status", "אפשר לאשר רק משתמש בהמתנה")
    now = now_il()
    ref = db.collection("users").document(uid)
    # .update() writes aiBudgetUsd explicitly, including null (Unlimited) — not dropped.
    ref.update(
        {
            "status": "active",
            "aiBudgetUsd": ai_budget_usd,
            "approvedByUid": admin_uid,
            "approvedAt": now,
            "updatedAt": now,
        }
    )
    return User.model_validate(ref.get().to_dict())


def set_user_status(db: firestore.Client, admin_uid: str, uid: str, target: str) -> User:
    if target == "disabled" and uid == admin_uid:
        api_error(409, "cannot_disable_self", "אי אפשר להשבית את עצמך")
    _get_user_or_404(db, uid)
    ref = db.collection("users").document(uid)
    ref.update({"status": target, "updatedAt": now_il()})
    return User.model_validate(ref.get().to_dict())


def set_user_role(db: firestore.Client, admin_uid: str, uid: str, role: str) -> User:
    if uid == admin_uid:
        api_error(409, "cannot_change_own_role", "אי אפשר לשנות את התפקיד של עצמך")
    _get_user_or_404(db, uid)
    ref = db.collection("users").document(uid)
    ref.update({"role": role, "updatedAt": now_il()})
    return User.model_validate(ref.get().to_dict())


def set_user_budget(db: firestore.Client, uid: str, ai_budget_usd: float | None) -> User:
    _get_user_or_404(db, uid)
    ref = db.collection("users").document(uid)
    # null is allowed (Unlimited) and written explicitly via .update().
    ref.update({"aiBudgetUsd": ai_budget_usd, "updatedAt": now_il()})
    return User.model_validate(ref.get().to_dict())

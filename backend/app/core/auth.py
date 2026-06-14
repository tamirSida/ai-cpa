import logging
from dataclasses import dataclass

from fastapi import Depends, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth as fb_auth
from google.cloud import firestore

from app.core.config import get_settings
from app.core.errors import api_error
from app.core.firebase import get_db
from app.schemas.business import Business
from app.schemas.user import User
from app.services import user_service

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=False)  # auto_error=True would emit 403 without our error shape


@dataclass
class TokenIdentity:
    uid: str
    email: str | None
    name: str | None


def get_token_identity(
    creds: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> TokenIdentity:
    if creds is None:
        api_error(401, "unauthenticated", "Missing Authorization header")
    try:
        decoded = fb_auth.verify_id_token(creds.credentials)  # no check_revoked (locked decision)
    except (ValueError, fb_auth.InvalidIdTokenError):
        # Token is malformed/expired/wrong-audience — a client problem: 401.
        api_error(401, "invalid_token", "Invalid or expired ID token")
    except Exception:
        # Uninitialized firebase app, JWKS fetch failure, etc. — a server problem: 500.
        logger.exception("Unexpected error during token verification")
        raise
    return TokenIdentity(uid=decoded["uid"], email=decoded.get("email"), name=decoded.get("name"))


def get_current_uid(
    creds: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> str:
    # Delegates so the verification logic lives in one place; same signature/behavior as
    # before, so existing routes (and test overrides of get_current_uid) are unaffected.
    return get_token_identity(creds).uid


def get_current_user(
    identity: TokenIdentity = Depends(get_token_identity),
    db: firestore.Client = Depends(get_db),
) -> User:
    # Lazily ensures users/{uid} on first sign-in; no status gate (callers decide).
    return user_service.ensure_user(
        db, uid=identity.uid, email=identity.email, name=identity.name, settings=get_settings()
    )


def require_active(user: User = Depends(get_current_user)) -> User:
    if user.status == "pending":
        api_error(403, "account_pending", "Your account is awaiting admin approval")
    if user.status == "disabled":
        api_error(403, "account_disabled", "Your account has been disabled")
    return user


def get_current_admin(user: User = Depends(require_active)) -> User:
    if user.role != "admin":
        api_error(403, "forbidden_not_admin", "Admin access required")
    return user


def get_owned_business(
    businessId: str,  # matches the {businessId} path param on every business-scoped route
    uid: str = Depends(get_current_uid),
    db: firestore.Client = Depends(get_db),
) -> Business:
    snap = db.collection("businesses").document(businessId).get()
    if not snap.exists:
        api_error(404, "business_not_found", "Business not found")
    data = snap.to_dict()
    if data.get("ownerUserId") != uid:
        api_error(403, "forbidden", "You do not own this business")
    return Business.model_validate({**data, "id": snap.id})

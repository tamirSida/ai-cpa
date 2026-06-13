import logging

from fastapi import Depends, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth as fb_auth
from google.cloud import firestore

from app.core.errors import api_error
from app.core.firebase import get_db
from app.schemas.business import Business

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=False)  # auto_error=True would emit 403 without our error shape


def get_current_uid(
    creds: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> str:
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
    return decoded["uid"]


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

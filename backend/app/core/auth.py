from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.errors import api_error

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_uid(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    # Phase 0 seam: Phase 1 replaces this body with firebase_admin.auth.verify_id_token.
    api_error(401, "auth/not-configured", "Authentication is not configured yet")

from fastapi import APIRouter, Depends
from google.cloud import firestore

from app.core.auth import get_current_user
from app.core.firebase import get_db
from app.schemas.user import MeResponse, User
from app.services import business_service, usage_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=MeResponse)
def get_me(
    user: User = Depends(get_current_user),
    db: firestore.Client = Depends(get_db),
) -> MeResponse:
    # Depends on get_current_user (ensures the doc) — NOT require_active — so pending/disabled
    # users can call this to learn their status (frontend decides which screen to show).
    usage = usage_service.usage_summary(db, user)
    has_business = business_service.get_business_by_owner(db, user.uid) is not None
    return MeResponse(
        uid=user.uid,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        status=user.status,
        ai_budget_usd=user.ai_budget_usd,
        usage=usage,
        has_business=has_business,
    )

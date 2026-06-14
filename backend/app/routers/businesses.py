from fastapi import APIRouter, Depends
from google.cloud import firestore

from app.core.auth import get_owned_business, require_active
from app.core.errors import api_error
from app.core.firebase import get_db
from app.schemas.business import Business, BusinessCreate, BusinessUpdate
from app.schemas.user import User
from app.services import business_service

router = APIRouter(prefix="/businesses", tags=["businesses"])


@router.post("", response_model=Business, status_code=201)
def create_business(
    payload: BusinessCreate,
    user: User = Depends(require_active),  # pending/disabled users can't even onboard
    db: firestore.Client = Depends(get_db),
) -> Business:
    return business_service.create_business(db, user.uid, payload)


@router.get("/me", response_model=Business)
def get_my_business(
    user: User = Depends(require_active),  # pending/disabled users can't even onboard
    db: firestore.Client = Depends(get_db),
) -> Business:
    business = business_service.get_business_by_owner(db, user.uid)
    if business is None:
        api_error(404, "business_not_found", "No business for this user")
    return business


@router.patch("/{businessId}", response_model=Business)
def patch_business(
    patch: BusinessUpdate,
    business: Business = Depends(get_owned_business),
    db: firestore.Client = Depends(get_db),
) -> Business:
    return business_service.update_business(db, business.id, patch)

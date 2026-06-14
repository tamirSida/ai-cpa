from fastapi import APIRouter, Depends
from google.cloud import firestore

from app.core.auth import get_current_admin
from app.core.firebase import get_db
from app.schemas.invite import Invite, InviteCreate
from app.schemas.user import User
from app.services import admin_service

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/invites", response_model=list[Invite])
def list_invites(
    status: str | None = None,
    admin: User = Depends(get_current_admin),
    db: firestore.Client = Depends(get_db),
) -> list[Invite]:
    return admin_service.list_invites(db, status)


@router.post("/invites", response_model=Invite, status_code=201)
def create_invite(
    payload: InviteCreate,
    admin: User = Depends(get_current_admin),
    db: firestore.Client = Depends(get_db),
) -> Invite:
    return admin_service.create_invite(db, admin.uid, payload.email)


@router.delete("/invites/{email}")
def revoke_invite(
    email: str,
    admin: User = Depends(get_current_admin),
    db: firestore.Client = Depends(get_db),
) -> dict:
    return admin_service.revoke_invite(db, email)

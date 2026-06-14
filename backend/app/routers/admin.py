from fastapi import APIRouter, Depends
from google.cloud import firestore

from app.core.auth import get_current_admin
from app.core.firebase import get_db
from app.schemas.invite import Invite, InviteCreate
from app.schemas.user import (
    AdminUserDetail,
    ApproveRequest,
    BudgetRequest,
    RoleRequest,
    User,
)
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


# --- user management --------------------------------------------------------

@router.get("/users", response_model=list[User])
def list_users(
    status: str | None = None,
    q: str | None = None,
    limit: int = 50,
    admin: User = Depends(get_current_admin),
    db: firestore.Client = Depends(get_db),
) -> list[User]:
    return admin_service.list_users(db, status, q, limit)


@router.get("/users/{uid}", response_model=AdminUserDetail)
def get_user_detail(
    uid: str,
    admin: User = Depends(get_current_admin),
    db: firestore.Client = Depends(get_db),
) -> AdminUserDetail:
    return admin_service.get_user_detail(db, uid)


@router.post("/users/{uid}/approve", response_model=User)
def approve_user(
    uid: str,
    payload: ApproveRequest,
    admin: User = Depends(get_current_admin),
    db: firestore.Client = Depends(get_db),
) -> User:
    return admin_service.approve_user(db, admin.uid, uid, payload.ai_budget_usd)


@router.post("/users/{uid}/enable", response_model=User)
def enable_user(
    uid: str,
    admin: User = Depends(get_current_admin),
    db: firestore.Client = Depends(get_db),
) -> User:
    return admin_service.set_user_status(db, admin.uid, uid, "active")


@router.post("/users/{uid}/disable", response_model=User)
def disable_user(
    uid: str,
    admin: User = Depends(get_current_admin),
    db: firestore.Client = Depends(get_db),
) -> User:
    return admin_service.set_user_status(db, admin.uid, uid, "disabled")


@router.post("/users/{uid}/role", response_model=User)
def set_user_role(
    uid: str,
    payload: RoleRequest,
    admin: User = Depends(get_current_admin),
    db: firestore.Client = Depends(get_db),
) -> User:
    return admin_service.set_user_role(db, admin.uid, uid, payload.role)


@router.post("/users/{uid}/budget", response_model=User)
def set_user_budget(
    uid: str,
    payload: BudgetRequest,
    admin: User = Depends(get_current_admin),
    db: firestore.Client = Depends(get_db),
) -> User:
    return admin_service.set_user_budget(db, uid, payload.ai_budget_usd)

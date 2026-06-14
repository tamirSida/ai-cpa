from datetime import datetime
from typing import Literal, Optional

from app.schemas.common import CamelModel

InviteStatus = Literal["pending", "accepted", "revoked"]


class Invite(CamelModel):
    id: str  # == normalized email (the doc id); convenient for the frontend
    email: str  # normalized lowercase (== id)
    status: InviteStatus = "pending"
    invited_by_uid: str
    accepted_by_uid: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class InviteCreate(CamelModel):
    email: str

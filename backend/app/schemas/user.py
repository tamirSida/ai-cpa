from datetime import datetime
from typing import Literal, Optional

from app.schemas.common import CamelModel

Role = Literal["admin", "user"]
Status = Literal["pending", "active", "disabled"]


class User(CamelModel):
    uid: str
    email: str  # normalized lowercase
    display_name: Optional[str] = None
    role: Role = "user"
    status: Status = "pending"
    ai_budget_usd: Optional[float] = None  # None == Unlimited
    invited_by_uid: Optional[str] = None
    approved_by_uid: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

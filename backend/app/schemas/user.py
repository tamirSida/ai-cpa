from datetime import datetime
from typing import Literal, Optional

from pydantic import Field

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


class UsageSummary(CamelModel):
    month: str  # "YYYY-MM"
    ai_cost_usd: float
    ai_budget_usd: Optional[float]  # echoed from the user (None == Unlimited)
    over_budget: bool  # cost >= budget (False when budget is None)


class MeResponse(CamelModel):
    uid: str
    email: str
    display_name: Optional[str]
    role: Role
    status: Status
    ai_budget_usd: Optional[float]
    usage: UsageSummary
    has_business: bool


class BusinessSummary(CamelModel):
    id: str
    business_name: str
    business_id_number: str


class AdminUserDetail(User):  # inherits all User fields
    usage: UsageSummary
    business: Optional[BusinessSummary] = None


class ApproveRequest(CamelModel):
    # omitted -> $3 default; explicit null -> Unlimited.
    # When not null: must be a finite number >= 0 (rejects negative / NaN / Infinity).
    ai_budget_usd: Optional[float] = Field(default=3.0, ge=0, allow_inf_nan=False)


class RoleRequest(CamelModel):
    role: Role


class BudgetRequest(CamelModel):
    # null -> Unlimited. When not null: must be a finite number >= 0
    # (rejects negative / NaN / Infinity).
    ai_budget_usd: Optional[float] = Field(default=None, ge=0, allow_inf_nan=False)

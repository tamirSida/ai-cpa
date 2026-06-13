from datetime import datetime
from typing import Literal, Optional

from pydantic import ConfigDict, Field

from app.schemas.common import CamelModel


class BusinessCreate(CamelModel):
    business_name: str = Field(min_length=1, max_length=120)
    owner_name: str = Field(min_length=1, max_length=120)
    business_id_number: str = Field(pattern=r"^\d{5,9}$")  # ת.ז / ע.מ digits only
    address: str = Field(min_length=1, max_length=200)
    phone: Optional[str] = None
    email: Optional[str] = None
    receipt_prefix: Optional[str] = Field(default=None, max_length=10)  # server defaults to current IL year


class BusinessUpdate(CamelModel):
    # extra="forbid": sending nextReceiptNumber/businessType/etc. -> FastAPI 422
    model_config = CamelModel.model_config | ConfigDict(extra="forbid")
    business_name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    owner_name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    address: Optional[str] = Field(default=None, min_length=1, max_length=200)
    phone: Optional[str] = None
    email: Optional[str] = None
    receipt_prefix: Optional[str] = Field(default=None, min_length=1, max_length=10)


class Business(CamelModel):
    id: str
    owner_user_id: str
    business_name: str
    owner_name: str
    business_id_number: str
    business_type: Literal["osek_patur"] = "osek_patur"
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    receipt_prefix: str
    next_receipt_number: int = 1
    annual_limit: Optional[int] = None
    created_at: datetime
    updated_at: datetime

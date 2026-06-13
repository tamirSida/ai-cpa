# backend/app/schemas/expense.py
from datetime import datetime
from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

class _Camel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, use_enum_values=True)

class ExpenseCategory(str, Enum):
    SOFTWARE = "software"; EQUIPMENT = "equipment"; TRAVEL = "travel"; OFFICE = "office"
    MARKETING = "marketing"; PROFESSIONAL_SERVICES = "professional_services"
    MEALS = "meals"; PARKING = "parking"; OTHER = "other"

VALID_CATEGORIES = {c.value for c in ExpenseCategory}
ExpenseStatus = Literal["needs_review", "approved", "rejected"]

class Expense(_Camel):
    id: str
    business_id: str
    supplier_name: Optional[str] = None
    expense_date: Optional[str] = None          # ISO YYYY-MM-DD
    amount: Optional[float] = None
    currency: Literal["ILS"] = "ILS"
    category: Optional[ExpenseCategory] = None
    description: Optional[str] = None
    business_use_percent: int = 100
    image_url: Optional[str] = None
    cloudinary_public_id: Optional[str] = None
    ocr_text: Optional[str] = None
    extraction_confidence: Optional[float] = None
    status: ExpenseStatus
    created_at: datetime
    updated_at: datetime

class ExpenseCreate(_Camel):
    supplier_name: Optional[str] = None
    expense_date: Optional[str] = None
    amount: Optional[float] = Field(default=None, gt=0)   # amount <= 0 -> FastAPI 422
    category: Optional[ExpenseCategory] = None
    description: Optional[str] = None
    business_use_percent: Optional[int] = None            # clamped 0-100 in service, default 100
    image_url: Optional[str] = None                       # set by upload route only
    cloudinary_public_id: Optional[str] = None

class ExpensePatch(_Camel):   # exactly the editable whitelist — nothing else is patchable
    supplier_name: Optional[str] = None
    expense_date: Optional[str] = None
    amount: Optional[float] = Field(default=None, gt=0)
    category: Optional[ExpenseCategory] = None
    description: Optional[str] = None
    business_use_percent: Optional[int] = None

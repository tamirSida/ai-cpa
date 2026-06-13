# backend/app/schemas/expense.py
from datetime import datetime
from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

class _Camel(BaseModel):
    # Local base (NOT app.schemas.common.CamelModel) precisely because it adds use_enum_values=True:
    # ExpenseCategory is the only CamelModel-domain Enum field, and we want it persisted to Firestore
    # as a plain string ("software"), not an enum member. The shared CamelModel is left untouched so
    # this config can't leak into the ~10 schemas that inherit it.
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
    business_use_percent: int = 100  # always 0-100 (service clamps inputs before building this record)
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
    business_use_percent: Optional[int] = None            # service clamps to 0-100, defaults to 100
    image_url: Optional[str] = None                       # set by upload route only
    cloudinary_public_id: Optional[str] = None

class ExpensePatch(_Camel):   # exactly the editable whitelist — nothing else is patchable
    supplier_name: Optional[str] = None
    expense_date: Optional[str] = None
    amount: Optional[float] = Field(default=None, gt=0)
    category: Optional[ExpenseCategory] = None
    description: Optional[str] = None
    business_use_percent: Optional[int] = None            # service clamps to 0-100

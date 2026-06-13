from enum import Enum
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class IntentType(str, Enum):
    CREATE_RECEIPT = "CREATE_RECEIPT"
    CREATE_CONTACT = "CREATE_CONTACT"
    CREATE_EXPENSE = "CREATE_EXPENSE"
    QUERY = "QUERY"
    GENERATE_ANNUAL_REPORT = "GENERATE_ANNUAL_REPORT"
    UNKNOWN = "UNKNOWN"


class PaymentMethod(str, Enum):
    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"
    BIT = "bit"
    PAYBOX = "paybox"
    CREDIT_CARD = "credit_card"
    CHECK = "check"
    OTHER = "other"
    UNKNOWN = "unknown"


class TimePreset(str, Enum):
    TODAY = "TODAY"
    THIS_WEEK = "THIS_WEEK"
    THIS_MONTH = "THIS_MONTH"
    THIS_YEAR = "THIS_YEAR"
    LAST_YEAR = "LAST_YEAR"
    ALL_TIME = "ALL_TIME"
    CUSTOM = "CUSTOM"


class QueryType(str, Enum):
    TOTAL_REVENUE = "TOTAL_REVENUE"
    TOTAL_EXPENSES = "TOTAL_EXPENSES"
    ESTIMATED_PROFIT = "ESTIMATED_PROFIT"
    CLIENT_REVENUE = "CLIENT_REVENUE"
    CONTACT_EXISTS = "CONTACT_EXISTS"
    RECEIPTS_COUNT = "RECEIPTS_COUNT"
    EXPENSES_BY_CATEGORY = "EXPENSES_BY_CATEGORY"
    OSEK_PATUR_LIMIT_STATUS = "OSEK_PATUR_LIMIT_STATUS"
    UNKNOWN = "UNKNOWN"


class TimeRange(BaseModel):
    preset: Optional[TimePreset] = None          # server default: THIS_YEAR
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class ReceiptPayload(BaseModel):
    client_name: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[Literal["ILS"]] = None    # server default: ILS
    description: Optional[str] = None
    payment_method: Optional[PaymentMethod] = None   # server default: unknown
    payment_received: Optional[bool] = None
    issue_receipt: Optional[bool] = None
    check_number: Optional[str] = None
    check_bank: Optional[str] = None
    check_branch: Optional[str] = None
    check_due_date: Optional[str] = None


class ContactPayload(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company_name: Optional[str] = None
    tax_id: Optional[str] = None
    address: Optional[str] = None


class ExpensePayload(BaseModel):
    supplier_name: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[Literal["ILS"]] = None
    category: Optional[str] = None
    description: Optional[str] = None
    business_use_percent: Optional[int] = Field(default=None, ge=0, le=100)  # server default: 100
    expense_date: Optional[str] = None


class QueryPayload(BaseModel):
    type: Optional[QueryType] = None
    time_range: Optional[TimeRange] = None
    client_name: Optional[str] = None
    metric: Optional[str] = None


class ParsedUserCommand(BaseModel):
    intent: IntentType
    confidence: Optional[float] = Field(default=None, ge=0, le=1)
    language: Optional[Literal["he", "en", "mixed", "unknown"]] = None
    receipt: Optional[ReceiptPayload] = None
    contact: Optional[ContactPayload] = None
    expense: Optional[ExpensePayload] = None
    query: Optional[QueryPayload] = None
    missing_fields: Optional[List[str]] = None   # NEVER trusted; recomputed server-side
    requires_confirmation: Optional[bool] = None
    user_facing_message: Optional[str] = None
    resolved_from_context: Optional[bool] = None


class ExpenseCategory(str, Enum):
    SOFTWARE = "software"; EQUIPMENT = "equipment"; TRAVEL = "travel"; OFFICE = "office"
    MARKETING = "marketing"; PROFESSIONAL_SERVICES = "professional_services"
    MEALS = "meals"; PARKING = "parking"; OTHER = "other"


class ExpenseExtraction(BaseModel):
    supplier_name: Optional[str] = None
    expense_date: Optional[str] = None           # ISO YYYY-MM-DD
    amount: Optional[float] = None
    currency: Optional[Literal["ILS"]] = None
    category: Optional[ExpenseCategory] = None
    description: Optional[str] = None
    ocr_text: Optional[str] = None
    confidence: Optional[float] = Field(default=None, ge=0, le=1)


class ParserFailure(BaseModel):                  # internal, never sent to OpenAI
    reason: Literal["refusal", "validation_error", "timeout", "rate_limit", "api_error", "length"]
    detail: str = ""

# backend/app/schemas/receipt.py
from datetime import datetime
from typing import Literal
from app.schemas.common import CamelModel

PaymentMethod = Literal["cash", "bank_transfer", "bit", "paybox", "credit_card", "check", "other", "unknown"]
ReceiptStatus = Literal["draft", "issued", "cancelled"]

class ClientSnapshot(CamelModel):
    name: str
    phone: str | None = None
    email: str | None = None
    tax_id: str | None = None
    address: str | None = None

class CheckDetails(CamelModel):
    number: str
    bank: str
    branch: str
    due_date: str  # ISO YYYY-MM-DD; wire alias dueDate

class ReceiptDraftCreate(CamelModel):
    client_id: str | None = None
    client_name: str | None = None
    amount: float
    currency: Literal["ILS"] = "ILS"
    description: str
    payment_method: PaymentMethod = "unknown"
    check_details: CheckDetails | None = None
    issue_date: str | None = None  # ISO YYYY-MM-DD; defaults to today_il()

class ReceiptCancelRequest(CamelModel):
    reason: str

class Receipt(CamelModel):
    id: str
    business_id: str
    client_id: str | None = None
    receipt_number: str | None = None
    sequence_number: int | None = None
    status: ReceiptStatus
    issue_date: str
    amount: float
    currency: Literal["ILS"] = "ILS"
    payment_method: PaymentMethod
    description: str
    check_details: CheckDetails | None = None
    client_snapshot: ClientSnapshot
    pdf_url: str | None = None
    cloudinary_public_id: str | None = None
    created_at: datetime
    issued_at: datetime | None = None
    cancelled_at: datetime | None = None
    cancellation_reason: str | None = None

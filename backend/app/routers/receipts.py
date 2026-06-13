from typing import Literal

from fastapi import APIRouter, Depends

from app.core.auth import get_owned_business
from app.core.errors import api_error
from app.core.firebase import get_db
from app.schemas.business import Business
from app.schemas.receipt import Receipt, ReceiptCancelRequest, ReceiptDraftCreate
from app.services import receipt_service

router = APIRouter(prefix="/businesses/{businessId}/receipts", tags=["receipts"])


@router.post("/draft", response_model=Receipt, status_code=201)
def create_draft(payload: ReceiptDraftCreate, business: Business = Depends(get_owned_business), db=Depends(get_db)):
    return receipt_service.create_draft(db, business, payload)


@router.post("/{receipt_id}/issue", response_model=Receipt)
def issue_receipt(receipt_id: str, business: Business = Depends(get_owned_business), db=Depends(get_db)):
    return receipt_service.issue_receipt(db, business.id, receipt_id)


@router.post("/{receipt_id}/cancel", response_model=Receipt)
def cancel_receipt(receipt_id: str, body: ReceiptCancelRequest, business: Business = Depends(get_owned_business), db=Depends(get_db)):
    return receipt_service.cancel_receipt(db, business.id, receipt_id, body.reason)


@router.get("", response_model=list[Receipt])
def list_receipts(status: Literal["draft", "issued", "cancelled"] | None = None, year: int | None = None, business: Business = Depends(get_owned_business), db=Depends(get_db)):
    return receipt_service.list_receipts(db, business.id, status, year)


@router.get("/{receipt_id}", response_model=Receipt)
def get_receipt(receipt_id: str, business: Business = Depends(get_owned_business), db=Depends(get_db)):
    receipt = receipt_service.get_receipt(db, business.id, receipt_id)
    if receipt is None:
        api_error(404, "receipt_not_found", "קבלה לא נמצאה")
    return receipt

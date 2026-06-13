from fastapi import APIRouter, Depends, File, UploadFile
from app.core.auth import get_owned_business
from app.core.errors import api_error
from app.core.firebase import get_db
from app.schemas.business import Business
from app.schemas.expense import Expense, ExpenseCreate, ExpensePatch
from app.services import cloudinary_service, expense_service   # module-style import: tests monkeypatch attributes
from app.services.openai_service import CommandParser, get_command_parser

router = APIRouter(prefix="/businesses/{businessId}/expenses", tags=["expenses"])
VALID_STATUSES = {"needs_review", "approved", "rejected"}
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/heic", "image/webp"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

@router.post("", response_model=Expense, status_code=201)
def create_manual_expense(payload: ExpenseCreate,
                          business: Business = Depends(get_owned_business), db=Depends(get_db)):
    return expense_service.create_expense(db, business.id, payload, source="manual")

@router.get("", response_model=list[Expense])
def list_expenses(status: str | None = None, year: int | None = None,
                  business: Business = Depends(get_owned_business), db=Depends(get_db)):
    if status is not None and status not in VALID_STATUSES:
        api_error(422, "invalid_status_filter", "סטטוס לא חוקי: needs_review / approved / rejected")
    return expense_service.list_expenses(db, business.id, status=status, year=year)

@router.patch("/{expense_id}", response_model=Expense)
def patch_expense(expense_id: str, patch: ExpensePatch,
                  business: Business = Depends(get_owned_business), db=Depends(get_db)):
    return expense_service.update_expense(db, business.id, expense_id, patch)

@router.post("/{expense_id}/approve", response_model=Expense)
def approve(expense_id: str, business: Business = Depends(get_owned_business), db=Depends(get_db)):
    return expense_service.approve_expense(db, business.id, expense_id)

@router.post("/{expense_id}/reject", response_model=Expense)
def reject(expense_id: str, business: Business = Depends(get_owned_business), db=Depends(get_db)):
    return expense_service.reject_expense(db, business.id, expense_id)

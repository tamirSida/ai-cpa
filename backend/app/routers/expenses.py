from fastapi import APIRouter, Depends, File, UploadFile
from app.core.auth import get_owned_business, require_active
from app.core.errors import api_error
from app.core.firebase import get_db
from app.schemas.business import Business
from app.schemas.expense import Expense, ExpenseCreate, ExpensePatch
from app.schemas.user import User
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

@router.post("/upload", response_model=Expense, status_code=201)
def upload_expense_image(file: UploadFile = File(...),
                         business: Business = Depends(get_owned_business), db=Depends(get_db)):
    # content_type is client-supplied (spoofable) — this is a fast-reject UX guard, NOT the real
    # gatekeeper: Cloudinary validates the actual bytes server-side and rejects non-images.
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        api_error(400, "unsupported_file_type", "סוג הקובץ לא נתמך. אפשר להעלות JPG, PNG, HEIC או WebP")
    data = file.file.read(MAX_UPLOAD_BYTES + 1)  # bounded read: never loads more than ~10MB+1
    if len(data) > MAX_UPLOAD_BYTES:
        api_error(413, "file_too_large", "הקובץ גדול מדי (מקסימום 10MB)")
    # If create_expense fails after this upload, the Cloudinary asset is orphaned — accepted MVP
    # leakage (a periodic cleanup job is backlog, not blocking for single-user scale).
    uploaded = cloudinary_service.upload_image(data, folder=f"expenses/{business.id}")
    payload = ExpenseCreate(image_url=uploaded.secure_url, cloudinary_public_id=uploaded.public_id)
    return expense_service.create_expense(db, business.id, payload, source="image")

@router.post("/{expense_id}/extract", response_model=Expense)
def extract(expense_id: str, business: Business = Depends(get_owned_business),
            user: User = Depends(require_active),  # cached per-request: reuses get_owned_business's user
            db=Depends(get_db), parser: CommandParser = Depends(get_command_parser)):
    return expense_service.run_extraction(db, business.id, expense_id, parser, user)

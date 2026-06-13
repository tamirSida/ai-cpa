# backend/app/services/expense_service.py
import cloudinary.utils
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from app.core.errors import api_error
from app.schemas.ai_commands import ExpenseExtraction
from app.schemas.expense import Expense, ExpenseCreate, ExpensePatch, VALID_CATEGORIES
from app.services.ledger_service import record_event
from app.services.openai_service import ParserFailure
from app.utils.dates import now_il, parse_iso_date
from app.utils.money import round_ils

ALLOWED_SOURCES = {"chat", "manual", "image"}
PATCH_WHITELIST = {"supplierName", "expenseDate", "amount", "category", "description", "businessUsePercent"}

def _expenses(db, business_id: str):
    return db.collection("businesses").document(business_id).collection("expenses")

def _clamp_pct(value) -> int:
    return 100 if value is None else max(0, min(100, int(value)))

def _load(db, business_id: str, expense_id: str):
    snap = _expenses(db, business_id).document(expense_id).get()
    if not snap.exists:
        api_error(404, "expense_not_found", "ההוצאה לא נמצאה")
    return snap.reference, snap.to_dict()

def _check_date(value: str | None) -> None:
    if value is not None and parse_iso_date(value) is None:
        api_error(422, "invalid_date", "תאריך ההוצאה חייב להיות בפורמט YYYY-MM-DD")

def create_expense(db, business_id: str, payload: ExpenseCreate, source: str) -> Expense:
    if source not in ALLOWED_SOURCES:
        raise ValueError(f"invalid expense source: {source}")
    if source != "image" and payload.amount is None:
        api_error(400, "missing_amount", "חסר סכום להוצאה")
    _check_date(payload.expense_date)
    if source == "image":
        status = "needs_review"          # vision results always reviewed by a human
    else:
        status = "approved" if payload.category is not None else "needs_review"  # doc §15
    now = now_il()
    ref = _expenses(db, business_id).document()
    data = {
        "id": ref.id, "businessId": business_id,
        "supplierName": payload.supplier_name, "expenseDate": payload.expense_date,
        "amount": round_ils(payload.amount) if payload.amount is not None else None,
        "currency": "ILS", "category": payload.category, "description": payload.description,
        "businessUsePercent": _clamp_pct(payload.business_use_percent),
        "imageUrl": payload.image_url, "cloudinaryPublicId": payload.cloudinary_public_id,
        "ocrText": None, "extractionConfidence": None,
        "status": status, "createdAt": now, "updatedAt": now,
    }
    ref.set(data)
    # create is a fresh insert + informational expense_created event; the dashboard/report read expenses by status, not the ledger, so a non-atomic event here is the least-consequential path.
    record_event(db, business_id, type="expense_created", entity_type="expense",
                 entity_id=ref.id, amount=data["amount"], metadata={"source": source})
    return Expense.model_validate(data)

def approve_expense(db, business_id: str, expense_id: str) -> Expense:
    ref = _expenses(db, business_id).document(expense_id)
    transaction = db.transaction()

    @firestore.transactional
    def _approve(tx) -> dict:
        snap = ref.get(transaction=tx)
        if not snap.exists:
            api_error(404, "expense_not_found", "ההוצאה לא נמצאה")
        data = snap.to_dict()
        if data["status"] != "needs_review":
            api_error(409, "invalid_expense_status", "אפשר לאשר רק הוצאה בסטטוס לבדיקה")
        if data.get("amount") is None:
            api_error(422, "missing_amount", "אי אפשר לאשר הוצאה ללא סכום")
        changes = {"status": "approved", "updatedAt": now_il()}
        tx.update(ref, changes)
        record_event(tx, business_id, type="expense_approved", entity_type="expense",
                     entity_id=expense_id, amount=data["amount"])
        return {**data, **changes}

    return Expense.model_validate(_approve(transaction))

def reject_expense(db, business_id: str, expense_id: str) -> Expense:
    ref = _expenses(db, business_id).document(expense_id)
    transaction = db.transaction()

    @firestore.transactional
    def _reject(tx) -> dict:
        snap = ref.get(transaction=tx)
        if not snap.exists:
            api_error(404, "expense_not_found", "ההוצאה לא נמצאה")
        data = snap.to_dict()
        if data["status"] != "needs_review":
            api_error(409, "invalid_expense_status", "אפשר לדחות רק הוצאה בסטטוס לבדיקה")
        changes = {"status": "rejected", "updatedAt": now_il()}
        tx.update(ref, changes)
        record_event(tx, business_id, type="expense_rejected", entity_type="expense",
                     entity_id=expense_id, amount=data.get("amount"))
        return {**data, **changes}

    return Expense.model_validate(_reject(transaction))

def list_expenses(db, business_id: str, status: str | None = None, year: int | None = None) -> list[Expense]:
    q = _expenses(db, business_id)
    if status is not None:
        q = q.where(filter=FieldFilter("status", "==", status))
    items = [s.to_dict() for s in q.stream()]
    if year is not None:  # filter in Python: avoids composite index + emulator/prod drift; MVP volumes are tiny
        items = [d for d in items if (d.get("expenseDate") or "").startswith(f"{year}-")]
    items.sort(key=lambda d: d["createdAt"], reverse=True)
    return [Expense.model_validate(d) for d in items]

def update_expense(db, business_id: str, expense_id: str, patch: ExpensePatch) -> Expense:
    ref, data = _load(db, business_id, expense_id)
    if data["status"] != "needs_review":
        api_error(409, "invalid_expense_status", "אפשר לערוך הוצאה רק כשהיא בסטטוס לבדיקה")
    changes = {k: v for k, v in patch.model_dump(by_alias=True, exclude_unset=True).items() if k in PATCH_WHITELIST}
    if not changes:
        api_error(422, "no_updatable_fields", "אין שדות לעדכון")
    _check_date(changes.get("expenseDate"))
    if changes.get("amount") is not None:
        changes["amount"] = round_ils(changes["amount"])
    if "businessUsePercent" in changes:
        changes["businessUsePercent"] = _clamp_pct(changes["businessUsePercent"])
    changes["updatedAt"] = now_il()
    ref.update(changes); data.update(changes)
    return Expense.model_validate(data)

def build_jpg_delivery_url(public_id: str) -> str:
    # f_jpg transformation: HEIC/WebP-safe JPEG delivery for the vision call (VERIFIED FACTS)
    url, _ = cloudinary.utils.cloudinary_url(public_id, resource_type="image", fetch_format="jpg", secure=True)
    return url

def run_extraction(db, business_id: str, expense_id: str, parser) -> Expense:
    # Not transactional: two concurrent /extract calls would both hit the LLM (double cost) and
    # last-writer-wins on the merge. Acceptable for single-user MVP (the review sheet calls this
    # once per expense); add an `extracting` soft-lock if multi-session extraction becomes real.
    ref, data = _load(db, business_id, expense_id)
    if data["status"] != "needs_review":
        api_error(409, "invalid_expense_status", "אפשר להריץ זיהוי רק על הוצאה בסטטוס לבדיקה")
    if not data.get("cloudinaryPublicId"):
        api_error(400, "no_image", "אין תמונה מצורפת להוצאה הזו")
    result = parser.extract_expense(build_jpg_delivery_url(data["cloudinaryPublicId"]))
    if isinstance(result, ParserFailure):
        api_error(502, "extraction_failed", "לא הצלחתי לחלץ נתונים מהתמונה, אפשר להזין ידנית")
    changes: dict = {}
    if result.supplier_name: changes["supplierName"] = result.supplier_name
    if result.amount is not None: changes["amount"] = round_ils(result.amount)
    if result.expense_date and parse_iso_date(result.expense_date): changes["expenseDate"] = result.expense_date
    if result.category in VALID_CATEGORIES: changes["category"] = result.category  # invalid LLM value -> dropped
    if result.description: changes["description"] = result.description
    if result.ocr_text: changes["ocrText"] = result.ocr_text
    if result.confidence is not None: changes["extractionConfidence"] = result.confidence
    changes["updatedAt"] = now_il()   # status untouched: stays needs_review
    ref.update(changes); data.update(changes)
    return Expense.model_validate(data)

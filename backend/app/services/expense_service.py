# backend/app/services/expense_service.py
from google.cloud.firestore_v1.base_query import FieldFilter
from app.core.errors import api_error
from app.schemas.expense import Expense, ExpenseCreate, ExpensePatch
from app.services.ledger_service import record_event
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
    record_event(db, business_id, type="expense_created", entity_type="expense",
                 entity_id=ref.id, amount=data["amount"], metadata={"source": source})
    return Expense.model_validate(data)

def approve_expense(db, business_id: str, expense_id: str) -> Expense:
    ref, data = _load(db, business_id, expense_id)
    if data["status"] != "needs_review":
        api_error(409, "invalid_expense_status", "אפשר לאשר רק הוצאה בסטטוס לבדיקה")
    if data.get("amount") is None:
        api_error(422, "missing_amount", "אי אפשר לאשר הוצאה ללא סכום")
    changes = {"status": "approved", "updatedAt": now_il()}
    ref.update(changes); data.update(changes)
    record_event(db, business_id, type="expense_approved", entity_type="expense",
                 entity_id=expense_id, amount=data["amount"])
    return Expense.model_validate(data)

def reject_expense(db, business_id: str, expense_id: str) -> Expense:
    ref, data = _load(db, business_id, expense_id)
    if data["status"] != "needs_review":
        api_error(409, "invalid_expense_status", "אפשר לדחות רק הוצאה בסטטוס לבדיקה")
    changes = {"status": "rejected", "updatedAt": now_il()}
    ref.update(changes); data.update(changes)
    record_event(db, business_id, type="expense_rejected", entity_type="expense",
                 entity_id=expense_id, amount=data.get("amount"))
    return Expense.model_validate(data)

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
    _check_date(changes.get("expenseDate"))
    if changes.get("amount") is not None:
        changes["amount"] = round_ils(changes["amount"])
    if "businessUsePercent" in changes:
        changes["businessUsePercent"] = _clamp_pct(changes["businessUsePercent"])
    changes["updatedAt"] = now_il()
    ref.update(changes); data.update(changes)
    return Expense.model_validate(data)

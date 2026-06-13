# backend/app/services/receipt_service.py
import logging
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from app.core.errors import api_error
from app.schemas.business import Business
from app.schemas.receipt import ClientSnapshot, Receipt, ReceiptDraftCreate
from app.services.client_service import get_client
from app.services.cloudinary_service import upload_pdf
from app.services.ledger_service import record_event
from app.services.pdf_service import render_pdf
from app.utils.dates import now_il, parse_iso_date, today_il
from app.utils.money import round_ils

logger = logging.getLogger(__name__)

def _col(db, business_id: str):
    return db.collection("businesses").document(business_id).collection("receipts")

def create_draft(db, business: Business, payload: ReceiptDraftCreate) -> Receipt:
    if payload.amount is None or payload.amount <= 0:
        api_error(422, "invalid_amount", "הסכום חייב להיות גדול מ-0")
    if not payload.description or not payload.description.strip():
        api_error(422, "invalid_description", "חסר תיאור לקבלה")
    if payload.issue_date is not None and parse_iso_date(payload.issue_date) is None:
        api_error(422, "invalid_issue_date", "תאריך לא תקין, נדרש YYYY-MM-DD")
    if payload.client_id:
        client = get_client(db, business.id, payload.client_id)
        if client is None:
            api_error(404, "client_not_found", "לקוח לא נמצא")
        snapshot = ClientSnapshot(name=client.name, phone=client.phone, email=client.email,
                                  tax_id=client.tax_id, address=client.address)
    elif payload.client_name and payload.client_name.strip():
        snapshot = ClientSnapshot(name=payload.client_name.strip())
    else:
        api_error(422, "missing_client", "נדרש מזהה לקוח קיים או שם לקוח")
    ref = _col(db, business.id).document()
    data = {"id": ref.id, "businessId": business.id, "clientId": payload.client_id,
            "status": "draft", "issueDate": payload.issue_date or today_il().isoformat(),
            "amount": round_ils(payload.amount), "currency": "ILS",
            "paymentMethod": payload.payment_method, "description": payload.description.strip(),
            "clientSnapshot": snapshot.model_dump(by_alias=True, exclude_none=True),
            "createdAt": now_il()}
    ref.set(data)
    return Receipt.model_validate(data)

def cancel_receipt(db, business_id: str, receipt_id: str, reason: str) -> Receipt:
    if not reason or not reason.strip():
        api_error(422, "missing_cancellation_reason", "נדרשת סיבת ביטול")
    ref = _col(db, business_id).document(receipt_id)
    transaction = db.transaction()

    @firestore.transactional
    def _cancel(tx) -> dict:
        snap = ref.get(transaction=tx)
        if not snap.exists:
            api_error(404, "receipt_not_found", "קבלה לא נמצאה")
        rec = snap.to_dict()
        if rec["status"] != "issued":
            api_error(409, "receipt_not_issued", "ניתן לבטל רק קבלה שהונפקה")
        updates = {"status": "cancelled", "cancellationReason": reason.strip(), "cancelledAt": now_il()}
        tx.update(ref, updates)
        record_event(tx, business_id, type="receipt_cancelled", entity_type="receipt",
                     entity_id=receipt_id, amount=rec["amount"], metadata={"reason": reason.strip()})
        return {**rec, **updates, "id": snap.id}

    return Receipt.model_validate(_cancel(transaction))

def issue_receipt(db, business_id: str, receipt_id: str) -> Receipt:
    business_ref = db.collection("businesses").document(business_id)
    receipt_ref = _col(db, business_id).document(receipt_id)
    # Non-transactional read: an optimisation to route the repair path, NOT a safety gate.
    # The authoritative status/draft check is the transactional read inside _issue (raises 409).
    pre = receipt_ref.get()
    if not pre.exists:
        api_error(404, "receipt_not_found", "קבלה לא נמצאה")
    pre_data = pre.to_dict()
    if pre_data["status"] == "issued" and not pre_data.get("pdfUrl"):
        _attach_pdf(db, business_id, receipt_ref)   # retry path: repair PDF, never re-number
        return Receipt.model_validate(receipt_ref.get().to_dict())

    @firestore.transactional
    def _issue(tx):
        biz_snap = business_ref.get(transaction=tx)
        rec_snap = receipt_ref.get(transaction=tx)
        biz, rec = biz_snap.to_dict(), rec_snap.to_dict()
        if biz.get("businessType") != "osek_patur":
            api_error(409, "unsupported_business_type", "נתמך רק עוסק פטור")
        if rec["status"] != "draft":
            # HTTPException is not a Firestore Aborted error, so the transaction wrapper
            # propagates it immediately — it does NOT burn the retry budget.
            api_error(409, "receipt_not_draft", "ניתן להנפיק רק קבלה בסטטוס טיוטה")
        sequence = biz["nextReceiptNumber"]          # ONE continuous sequence, never resets
        number = f"{biz['receiptPrefix']}-{sequence:04d}"
        now = now_il()
        tx.update(receipt_ref, {"receiptNumber": number, "sequenceNumber": sequence,
                                "status": "issued", "issuedAt": now,
                                "issueDate": rec.get("issueDate") or today_il().isoformat()})
        tx.update(business_ref, {"nextReceiptNumber": sequence + 1, "updatedAt": now})
        record_event(tx, business_id, type="receipt_issued", entity_type="receipt",
                     entity_id=receipt_id, amount=rec["amount"], metadata={"receiptNumber": number})

    # Each concurrent issuer contends for the single nextReceiptNumber counter; one continuous
    # sequence means a writer can lose the optimistic-concurrency race up to (N-1) times. Default
    # max_attempts=5 is too low for bursty issuing, so widen the retry budget — the numbering logic
    # is unchanged, only the retry count.
    _issue(db.transaction(max_attempts=25))  # auto-retried on contention -> atomic, gapless numbering
    try:
        _attach_pdf(db, business_id, receipt_ref)
    except Exception:
        # Receipt is legally issued without a PDF; Phase 6 precheck flags "receipts missing PDFs"
        # and re-POSTing /issue hits the repair branch above.
        logger.exception("post-commit PDF/upload failed for receipt %s", receipt_id)
    return Receipt.model_validate(receipt_ref.get().to_dict())

def _attach_pdf(db, business_id: str, receipt_ref) -> None:
    rec = receipt_ref.get().to_dict()
    biz = db.collection("businesses").document(business_id).get().to_dict()
    pdf = render_pdf("receipt.html", {"business": biz, "receipt": rec})
    up = upload_pdf(pdf, public_id=f"receipts/{business_id}/{rec['receiptNumber']}.pdf")
    receipt_ref.update({"pdfUrl": up.secure_url, "cloudinaryPublicId": up.public_id})

def list_receipts(db, business_id: str, status: str | None = None, year: int | None = None) -> list[Receipt]:
    q = _col(db, business_id)
    if status:
        q = q.where(filter=FieldFilter("status", "==", status))
    receipts = [Receipt.model_validate(d.to_dict()) for d in q.stream()]
    if year:  # issueDate is an ISO string; year filtered in Python to avoid a composite index at MVP scale
        receipts = [r for r in receipts if r.issue_date.startswith(f"{year}-")]
    return sorted(receipts, key=lambda r: r.created_at, reverse=True)

def get_receipt(db, business_id: str, receipt_id: str) -> Receipt | None:
    snap = _col(db, business_id).document(receipt_id).get()
    return Receipt.model_validate(snap.to_dict()) if snap.exists else None

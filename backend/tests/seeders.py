from datetime import datetime
from app.utils.dates import IL_TZ


def seed_receipt(db, bid, *, seq, amount, issue_date, issued_at=None,
                 status="issued", pdf_url=None, client_name="נועה"):
    doc = {
        "businessId": bid, "receiptNumber": f"2026-{seq:04d}", "sequenceNumber": seq,
        "status": status, "issueDate": issue_date, "amount": amount, "currency": "ILS",
        "paymentMethod": "bit", "description": "עיצוב לוגו",
        "clientSnapshot": {"name": client_name},
        "createdAt": issued_at or datetime.now(IL_TZ),
    }
    if status == "issued":
        doc["issuedAt"] = issued_at or datetime.now(IL_TZ)
    if pdf_url:
        doc["pdfUrl"] = pdf_url
        doc["cloudinaryPublicId"] = "tax/receipts/x"
    ref = db.collection("businesses").document(bid).collection("receipts").document()
    ref.set(doc)
    return ref.id


def seed_expense(db, bid, *, amount, status, category=None, expense_date=None,
                 supplier="Canva", use_pct=100, created_at=None):
    ts = created_at or datetime.now(IL_TZ)
    ref = db.collection("businesses").document(bid).collection("expenses").document()
    ref.set({
        "businessId": bid, "supplierName": supplier, "amount": amount, "currency": "ILS",
        "category": category, "description": None, "businessUsePercent": use_pct,
        "expenseDate": expense_date, "status": status, "createdAt": ts, "updatedAt": ts,
    })
    return ref.id

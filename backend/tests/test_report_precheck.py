# backend/tests/test_report_precheck.py
from app.utils.dates import now_il

def seed_receipt(db, biz_id, **over):
    doc = {"businessId": biz_id, "receiptNumber": "2026-0001", "sequenceNumber": 1, "status": "issued",
           "issueDate": "2026-03-01", "amount": 2800.0, "currency": "ILS", "paymentMethod": "bit",
           "description": "עיצוב לוגו", "clientSnapshot": {"name": "נועה"},
           "pdfUrl": "https://res.cloudinary.com/demo/raw/upload/r1.pdf",
           "createdAt": now_il(), "issuedAt": now_il()}
    doc.update(over)
    ref = db.collection("businesses").document(biz_id).collection("receipts").document()
    ref.set(doc); return ref.id

def seed_expense(db, biz_id, **over):
    doc = {"businessId": biz_id, "supplierName": "Canva", "expenseDate": "2026-02-10", "amount": 120.0,
           "currency": "ILS", "category": "software", "description": "מנוי", "businessUsePercent": 100,
           "imageUrl": "https://res.cloudinary.com/demo/image/upload/e1.jpg", "status": "approved",
           "createdAt": now_il(), "updatedAt": now_il()}
    doc.update(over)
    ref = db.collection("businesses").document(biz_id).collection("expenses").document()
    ref.set(doc); return ref.id

def test_precheck_flags_every_issue_type(api, db, make_business):
    biz = make_business(address=None, phone=None)
    e1 = seed_expense(db, biz["id"], status="needs_review", category=None, imageUrl=None)
    e2 = seed_expense(db, biz["id"], imageUrl=None)
    seed_receipt(db, biz["id"])
    seed_receipt(db, biz["id"], receiptNumber="2026-0002", sequenceNumber=2, pdfUrl=None)
    seed_receipt(db, biz["id"], receiptNumber="2026-0003", sequenceNumber=3, status="cancelled",
                 cancelledAt=now_il(), cancellationReason="טעות")
    r = api.post(f"/api/businesses/{biz['id']}/reports/annual/2026/precheck")
    assert r.status_code == 200
    d = r.json()
    assert d["expensesNeedingReview"] == [e1]
    assert sorted(d["expensesMissingImages"]) == sorted([e1, e2])
    assert d["uncategorizedExpenses"] == [e1]
    assert d["receiptsMissingPdf"] == ["2026-0002"]
    assert d["cancelledReceipts"] == ["2026-0003"]
    assert set(d["missingBusinessFields"]) >= {"address", "phone"}
    assert d["totalRevenue"] == 5600.0 and d["thresholdWarning"] is False and d["issuesCount"] == 8

def test_precheck_threshold_warning(api, db, make_business):
    biz = make_business()
    seed_receipt(db, biz["id"], amount=110000.0)
    d = api.post(f"/api/businesses/{biz['id']}/reports/annual/2026/precheck").json()
    assert d["thresholdWarning"] is True and d["totalRevenue"] == 110000.0

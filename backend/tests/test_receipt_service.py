# backend/tests/test_receipt_service.py
import pytest
from fastapi import HTTPException
from app.schemas.business import Business
from app.schemas.client import ClientCreate
from app.schemas.receipt import ReceiptDraftCreate
from app.services.client_service import create_client
from app.services import receipt_service as rs

def _biz(make_business, db):
    return Business.model_validate(make_business())

def test_create_draft_inline_name(db, make_business):
    biz = _biz(make_business, db)
    r = rs.create_draft(db, biz, ReceiptDraftCreate(client_name="נועה", amount=2800.005, description="עיצוב לוגו", payment_method="bit"))
    assert r.status == "draft" and r.amount == 2800.01 and r.client_snapshot.name == "נועה"
    assert r.receipt_number is None and r.issue_date  # defaults to today (Asia/Jerusalem)

def test_create_draft_from_client_id_snapshots_fields(db, make_business):
    biz = _biz(make_business, db)
    c = create_client(db, biz.id, ClientCreate(name="נועה גולן", phone="050-1234567", tax_id="200999888"))
    r = rs.create_draft(db, biz, ReceiptDraftCreate(client_id=c.id, amount=100, description="ייעוץ"))
    assert r.client_snapshot.phone == "050-1234567" and r.client_snapshot.tax_id == "200999888"

@pytest.mark.parametrize("kw,code", [
    (dict(client_name="נועה", amount=0, description="x"), "invalid_amount"),
    (dict(client_name="נועה", amount=-5, description="x"), "invalid_amount"),
    (dict(client_name="נועה", amount=10, description="  "), "invalid_description"),
    (dict(amount=10, description="x"), "missing_client"),
    (dict(client_name="נועה", amount=10, description="x", issue_date="13/06/2026"), "invalid_issue_date"),
])
def test_create_draft_validation(db, make_business, kw, code):
    biz = _biz(make_business, db)
    with pytest.raises(HTTPException) as e:
        rs.create_draft(db, biz, ReceiptDraftCreate(**kw))
    assert e.value.status_code in (404, 422) and e.value.detail["code"] == code

def test_draft_with_unknown_client_id_404(db, make_business):
    biz = _biz(make_business, db)
    with pytest.raises(HTTPException) as e:
        rs.create_draft(db, biz, ReceiptDraftCreate(client_id="nope", amount=10, description="x"))
    assert e.value.status_code == 404 and e.value.detail["code"] == "client_not_found"

def test_cancel_requires_issued_status(db, make_business):
    biz = _biz(make_business, db)
    r = rs.create_draft(db, biz, ReceiptDraftCreate(client_name="נועה", amount=10, description="x"))
    with pytest.raises(HTTPException) as e:
        rs.cancel_receipt(db, biz.id, r.id, "טעות")
    assert e.value.status_code == 409 and e.value.detail["code"] == "receipt_not_issued"

def test_cancel_issued_receipt_atomic(db, make_business):
    biz = make_business()
    business = Business.model_validate(biz)
    draft = rs.create_draft(db, business, ReceiptDraftCreate(client_name="נועה", amount=100, description="עיצוב"))
    # simulate issued state (issuing transaction itself lands in Task 2.7)
    db.collection("businesses").document(biz["id"]).collection("receipts") \
        .document(draft.id).update({"status": "issued", "receiptNumber": "2026-0001"})
    rec = rs.cancel_receipt(db, biz["id"], draft.id, "טעות בסכום")
    assert rec.status == "cancelled" and rec.cancellation_reason == "טעות בסכום"
    assert rec.cancelled_at is not None
    events = list(db.collection("businesses").document(biz["id"])
                  .collection("ledgerEvents").stream())
    assert any(e.to_dict()["type"] == "receipt_cancelled" for e in events)

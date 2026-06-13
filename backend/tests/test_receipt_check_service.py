# backend/tests/test_receipt_check_service.py
import pytest
from fastapi import HTTPException
from app.schemas.business import Business
from app.schemas.receipt import CheckDetails, ReceiptDraftCreate
from app.services import receipt_service

def test_check_payment_requires_details(db, make_business):
    business = Business.model_validate(make_business())
    with pytest.raises(HTTPException) as e:
        receipt_service.create_draft(db, business, ReceiptDraftCreate(
            client_name="נועה", amount=100.0, description="שיעור", payment_method="check"))
    assert e.value.status_code == 422 and e.value.detail["code"] == "missing_check_details"

def test_check_details_persisted(db, make_business):
    business = Business.model_validate(make_business())
    r = receipt_service.create_draft(db, business, ReceiptDraftCreate(
        client_name="נועה", amount=100.0, description="שיעור", payment_method="check",
        check_details=CheckDetails(number="55", bank="דיסקונט", branch="125", due_date="2026-05-01")))
    assert r.check_details.number == "55" and r.check_details.bank == "דיסקונט"

def test_non_check_nulls_details(db, make_business):
    business = Business.model_validate(make_business())
    r = receipt_service.create_draft(db, business, ReceiptDraftCreate(
        client_name="נועה", amount=100.0, description="שיעור", payment_method="bit",
        check_details=CheckDetails(number="55", bank="x", branch="1", due_date="2026-05-01")))
    assert r.check_details is None

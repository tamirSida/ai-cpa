# backend/tests/test_receipt_check_schema.py
from app.schemas.receipt import CheckDetails, Receipt, ReceiptDraftCreate

def test_check_details_round_trips_camelcase():
    cd = CheckDetails(number="123", bank="לאומי", branch="800", due_date="2026-05-01")
    assert cd.model_dump(by_alias=True) == {"number": "123", "bank": "לאומי", "branch": "800", "dueDate": "2026-05-01"}

def test_draft_create_accepts_check_details():
    d = ReceiptDraftCreate(client_name="נועה", amount=100.0, description="שיעור",
                           payment_method="check",
                           check_details=CheckDetails(number="1", bank="b", branch="2", due_date="2026-05-01"))
    assert d.check_details.number == "1"

def test_draft_create_check_details_optional():
    d = ReceiptDraftCreate(client_name="נועה", amount=100.0, description="שיעור")
    assert d.check_details is None

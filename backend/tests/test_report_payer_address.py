# backend/tests/test_report_payer_address.py
from app.schemas.business import Business
from app.services import report_service
from tests.test_report_precheck import seed_receipt

def test_precheck_flags_receipt_without_payer_address(db, make_business):
    business = Business.model_validate(make_business())
    # seed_receipt seeds an issued 2026 receipt whose clientSnapshot has no address
    seed_receipt(db, business.id)
    res = report_service.precheck(db, business, 2026)
    assert res.receipts_missing_payer_address  # non-empty

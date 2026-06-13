from app.schemas.ai_commands import IntentType
from app.services.chat_service import compute_missing_fields, merge_payload

R = IntentType.CREATE_RECEIPT
def test_receipt_all_present(): assert compute_missing_fields(R, {"client_name": "נועה", "amount": 2800,
    "description": "עיצוב לוגו", "payment_received": True}) == []
def test_receipt_missing_client(): assert "client_name" in compute_missing_fields(R, {"amount": 2800, "description": "x", "payment_received": True})
def test_receipt_missing_amount(): assert "amount" in compute_missing_fields(R, {"client_name": "נ", "description": "x", "payment_received": True})
def test_receipt_zero_amount_is_missing(): assert "amount" in compute_missing_fields(R, {"client_name": "נ", "amount": 0, "description": "x", "payment_received": True})
def test_receipt_missing_description(): assert "description" in compute_missing_fields(R, {"client_name": "נ", "amount": 1, "payment_received": True})
def test_payment_not_received_adds_pseudofield():
    assert "payment_received_confirmation" in compute_missing_fields(R, {"client_name": "נ", "amount": 1, "description": "x"})
def test_explicit_issue_request_satisfies_payment_rule():
    assert compute_missing_fields(R, {"client_name": "נ", "amount": 1, "description": "x", "issue_receipt": True}) == []
def test_contact_requires_name(): assert compute_missing_fields(IntentType.CREATE_CONTACT, {}) == ["name"]
def test_expense_requires_amount_only():
    assert compute_missing_fields(IntentType.CREATE_EXPENSE, {"supplier_name": "Canva"}) == ["amount"]
    assert compute_missing_fields(IntentType.CREATE_EXPENSE, {"amount": 120}) == []  # category optional -> needs_review later
def test_report_never_missing(): assert compute_missing_fields(IntentType.GENERATE_ANNUAL_REPORT, {"year": 2026}) == []

def test_merge_2800_bebit_case():  # doc §8: follow-up "2800 בביט"
    existing = {"client_name": "נועה", "description": "עיצוב לוגו", "amount": None, "payment_method": None}
    incoming = {"client_name": None, "description": None, "amount": 2800.0, "payment_method": "bit", "payment_received": True}
    m = merge_payload(existing, incoming, R)
    assert m["client_name"] == "נועה" and m["amount"] == 2800.0 and m["payment_method"] == "bit"
def test_merge_unknown_payment_method_never_overwrites():
    m = merge_payload({"payment_method": "bit"}, {"payment_method": "unknown"}, R)
    assert m["payment_method"] == "bit"
def test_merge_none_never_overwrites(): assert merge_payload({"amount": 5}, {"amount": None}, R)["amount"] == 5
def test_merge_explicit_correction_overwrites():
    assert merge_payload({"amount": 2800.0}, {"amount": 3000.0}, R)["amount"] == 3000.0

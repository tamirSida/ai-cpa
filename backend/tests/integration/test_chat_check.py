# backend/tests/integration/test_chat_check.py
from app.schemas.ai_commands import IntentType
from app.services.chat_service import compute_missing_fields
from app.utils.hebrew import build_followup_question

def test_check_payment_requires_check_fields():
    p = {"client_name": "נועה", "amount": 100.0, "description": "שיעור",
         "payment_received": True, "payment_method": "check"}
    missing = compute_missing_fields(IntentType.CREATE_RECEIPT, p)
    assert {"check_number", "check_bank", "check_branch", "check_due_date"} <= set(missing)

def test_non_check_no_check_fields():
    p = {"client_name": "נועה", "amount": 100.0, "description": "שיעור",
         "payment_received": True, "payment_method": "bit"}
    assert not any(f.startswith("check_") for f in compute_missing_fields(IntentType.CREATE_RECEIPT, p))

def test_followup_question_dedupes_check_fields():
    q = build_followup_question(IntentType.CREATE_RECEIPT, ["check_number", "check_bank", "check_branch", "check_due_date"])
    assert q.count("המחאה") == 1

# backend/tests/integration/test_chat_confirm.py
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi import HTTPException
from app.schemas.business import Business
from app.services import chat_service
from app.services.cloudinary_service import UploadResult
from tests.stubs import StubCommandParser
from tests.integration.test_chat_flow import FULL_RECEIPT, USER, _actions

@pytest.fixture(autouse=True)
def fake_pdf_and_cloudinary(monkeypatch):
    monkeypatch.setattr("app.services.pdf_service.render_pdf", lambda template_name, context: b"%PDF-1.4 fake")
    monkeypatch.setattr("app.services.cloudinary_service.upload_pdf",
        lambda data, public_id: UploadResult(secure_url=f"https://res.test/{public_id}", public_id=public_id))

@pytest.fixture
def pending_receipt(db, make_business):
    biz = Business.model_validate(make_business())
    stub = StubCommandParser().queue_command(FULL_RECEIPT)
    res = chat_service.handle_message(db, stub, biz, USER, "main", "קיבלתי 2800 מנועה על עיצוב לוגו בביט")
    return biz, res.action.id

def test_confirm_executes_receipt(db, pending_receipt):
    biz, action_id = pending_receipt
    res = chat_service.confirm_action(db, None, biz, action_id)
    assert res.result["receiptNumber"].endswith("-0001") and res.assistant_text == f"נוצרה קבלה מספר {res.result['receiptNumber']}."
    assert _actions(db, biz.id)[action_id]["status"] == "executed"

def test_fast_path_confirm_word_skips_llm(db, pending_receipt):
    biz, action_id = pending_receipt
    stub = StubCommandParser()                      # empty queue: any LLM call would assert
    res = chat_service.handle_message(db, stub, biz, USER, "main", "אישור")
    assert res.result and res.result["receiptId"] and stub.calls == []

def test_fast_path_cancel_word(db, pending_receipt):
    biz, action_id = pending_receipt
    res = chat_service.handle_message(db, StubCommandParser(), biz, USER, "main", "בטל")
    assert res.assistant_text == "הפעולה בוטלה."
    assert _actions(db, biz.id)[action_id]["cancellationReason"] == "user_cancelled"

def test_double_confirm_race_exactly_one_winner(db, pending_receipt):
    biz, action_id = pending_receipt
    def go():
        try: return chat_service.confirm_action(db, None, biz, action_id)
        except HTTPException as e: return e
    with ThreadPoolExecutor(max_workers=2) as ex:
        a, b = list(ex.map(lambda _: go(), range(2)))
    outcomes = sorted(type(x).__name__ for x in (a, b))
    assert outcomes == ["ExecutionResult", "HTTPException"]
    err = a if isinstance(a, HTTPException) else b
    assert err.status_code == 409 and err.detail["code"] == "action_not_confirmable"

def test_executor_failure_reverts_to_pending(db, pending_receipt, monkeypatch):
    biz, action_id = pending_receipt
    monkeypatch.setattr("app.services.receipt_service.issue_receipt",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    res = chat_service.confirm_action(db, None, biz, action_id)
    data = _actions(db, biz.id)[action_id]
    assert data["status"] == "pending_confirmation" and data["errorNote"] == "boom"
    assert res.assistant_text == "אירעה שגיאה בביצוע הפעולה. אפשר לנסות לאשר שוב."

def test_cancel_executed_action_is_409(db, pending_receipt):
    biz, action_id = pending_receipt
    chat_service.confirm_action(db, None, biz, action_id)
    with pytest.raises(HTTPException) as e:
        chat_service.cancel_action(db, biz.id, action_id)
    assert e.value.status_code == 409 and e.value.detail["code"] == "action_not_cancellable"

def test_retry_after_issue_failure_does_not_duplicate_receipt(db, pending_receipt, monkeypatch):
    biz, action_id = pending_receipt
    calls = {"n": 0}
    real_issue = chat_service.receipt_service.issue_receipt
    def flaky_issue(db_, bid, draft_id):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("transient issue failure")
        return real_issue(db_, bid, draft_id)
    monkeypatch.setattr("app.services.receipt_service.issue_receipt", flaky_issue)
    first = chat_service.confirm_action(db, None, biz, action_id)   # fails -> reverts to pending
    assert "אירעה שגיאה" in first.assistant_text
    second = chat_service.confirm_action(db, None, biz, action_id)  # retry -> SAME draft re-issued
    assert second.result["receiptNumber"].endswith("-0001")        # still the FIRST number, no duplicate
    # exactly ONE issued receipt exists for the business
    issued = [d.to_dict() for d in db.collection("businesses").document(biz.id).collection("receipts")
              .where(filter=chat_service.FieldFilter("status", "==", "issued")).stream()]
    assert len(issued) == 1 and issued[0]["receiptNumber"].endswith("-0001")

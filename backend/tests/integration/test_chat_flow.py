from datetime import timedelta
import pytest
from app.schemas.ai_commands import (ContactPayload, IntentType, ParsedUserCommand, ParserFailure,
                                     QueryPayload, QueryType, ReceiptPayload, TimePreset, TimeRange)
from app.schemas.business import Business
from app.services import chat_service
from app.utils.dates import now_il
from tests.stubs import StubCommandParser

FULL_RECEIPT = ParsedUserCommand(intent=IntentType.CREATE_RECEIPT, receipt=ReceiptPayload(
    client_name="נועה", amount=2800.0, description="עיצוב לוגו", payment_method="bit", payment_received=True))
PARTIAL_RECEIPT = ParsedUserCommand(intent=IntentType.CREATE_RECEIPT, receipt=ReceiptPayload(
    client_name="נועה", description="עיצוב לוגו", issue_receipt=True))
FOLLOWUP_AMOUNT = ParsedUserCommand(intent=IntentType.CREATE_RECEIPT, receipt=ReceiptPayload(
    amount=2800.0, payment_method="bit", payment_received=True))

@pytest.fixture
def biz(db, make_business): return Business.model_validate(make_business())

def _actions(db, bid):
    return {d.id: d.to_dict() for d in db.collection("businesses").document(bid).collection("pendingActions").stream()}

def test_happy_path_full_command_goes_to_pending_confirmation(db, biz):  # doc §14.1
    stub = StubCommandParser().queue_command(FULL_RECEIPT)
    res = chat_service.handle_message(db, stub, biz, "main", "קיבלתי 2800 מנועה על עיצוב לוגו בביט")
    assert res.action.status == "pending_confirmation" and res.action.missing_fields == []
    assert res.assistant_text.startswith("לאשר יצירת קבלה")
    msgs = list(db.collection("businesses").document(biz.id).collection("chatThreads")
                .document("main").collection("messages").stream())
    assert len(msgs) == 2  # user + assistant persisted

def test_followup_merge_flow(db, biz):  # doc §14.2
    stub = StubCommandParser().queue_command(PARTIAL_RECEIPT).queue_command(FOLLOWUP_AMOUNT)
    first = chat_service.handle_message(db, stub, biz, "main", "תוציא קבלה לנועה על עיצוב לוגו")
    assert first.action.status == "collecting_fields" and first.action.missing_fields == ["amount"]
    assert "סכום" in first.assistant_text
    second = chat_service.handle_message(db, stub, biz, "main", "2800 בביט")
    assert second.action.id == first.action.id and second.action.status == "pending_confirmation"
    assert second.action.payload["client_name"] == "נועה" and second.action.payload["amount"] == 2800.0
    # context sent to LLM contained the pending action (doc §8)
    assert stub.calls[1]["context"]["pending_action"]["payload"]["client_name"] == "נועה"

def test_query_during_pending_answers_and_reshows_question(db, biz):
    stub = StubCommandParser().queue_command(FULL_RECEIPT).queue_command(ParsedUserCommand(
        intent=IntentType.QUERY, query=QueryPayload(type=QueryType.TOTAL_REVENUE,
        time_range=TimeRange(preset=TimePreset.THIS_YEAR))))
    chat_service.handle_message(db, stub, biz, "main", "קיבלתי 2800 מנועה על עיצוב לוגו בביט")
    res = chat_service.handle_message(db, stub, biz, "main", "כמה כסף עשיתי השנה?")
    assert "ההכנסות שלך השנה" in res.assistant_text and "לאשר יצירת קבלה" in res.assistant_text
    assert res.action.status == "pending_confirmation"  # untouched

def test_different_create_intent_supersedes(db, biz):
    stub = StubCommandParser().queue_command(FULL_RECEIPT).queue_command(ParsedUserCommand(
        intent=IntentType.CREATE_CONTACT, contact=ContactPayload(name="דניאל")))
    old = chat_service.handle_message(db, stub, biz, "main", "קיבלתי 2800 מנועה על עיצוב לוגו בביט")
    new = chat_service.handle_message(db, stub, biz, "main", "יש לי לקוח חדש בשם דניאל")
    acts = _actions(db, biz.id)
    assert acts[old.action.id]["status"] == "cancelled" and acts[old.action.id]["cancellationReason"] == "superseded"
    assert new.action.type == "CREATE_CONTACT" and new.assistant_text == "לאשר יצירת איש קשר בשם דניאל?"

def test_unknown_intent_and_parser_failure_fallback(db, biz):
    stub = StubCommandParser().queue_command(ParsedUserCommand(intent=IntentType.UNKNOWN)) \
                              .queue_command(ParserFailure(reason="timeout"))
    for text in ("בלהבלה", "עוד בלהבלה"):
        res = chat_service.handle_message(db, stub, biz, "main", text)
        assert "לא הצלחתי להבין" in res.assistant_text and res.action is None

def test_stale_action_expires(db, biz):
    stub = StubCommandParser().queue_command(FULL_RECEIPT).queue_command(ParsedUserCommand(
        intent=IntentType.CREATE_CONTACT, contact=ContactPayload(name="דניאל")))
    old = chat_service.handle_message(db, stub, biz, "main", "קיבלתי 2800 מנועה על עיצוב לוגו בביט")
    db.collection("businesses").document(biz.id).collection("pendingActions") \
      .document(old.action.id).update({"updatedAt": now_il() - timedelta(hours=25)})
    chat_service.handle_message(db, stub, biz, "main", "לקוח חדש בשם דניאל")
    acts = _actions(db, biz.id)
    assert acts[old.action.id]["status"] == "cancelled" and acts[old.action.id]["cancellationReason"] == "expired"

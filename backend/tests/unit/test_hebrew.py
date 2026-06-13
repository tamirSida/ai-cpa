# backend/tests/unit/test_hebrew.py
from app.utils.hebrew import (normalize, CONFIRM_WORDS, CANCEL_WORDS,
    build_followup_question, build_confirmation_message, render_query_answer)
from app.schemas.ai_commands import IntentType, QueryType

def test_normalize(): assert normalize("  אִישור!! ") == "אִישור" and normalize("OK.") == "ok"
def test_confirm_cancel_words():
    assert normalize("אישור") in CONFIRM_WORDS and normalize("כן") in CONFIRM_WORDS and normalize("Yes") in CONFIRM_WORDS
    assert normalize("בטל") in CANCEL_WORDS and normalize("לא") in CANCEL_WORDS
def test_followup_combined():
    q = build_followup_question(IntentType.CREATE_RECEIPT, ["amount"])
    assert "סכום" in q and "אמצעי תשלום" in q   # doc §14.2 style combined question
def test_confirmation_receipt():
    msg = build_confirmation_message(IntentType.CREATE_RECEIPT,
        {"client_name": "נועה", "amount": 2800.0, "description": "עיצוב לוגו", "payment_method": "bit"})
    assert msg == "לאשר יצירת קבלה על ₪2,800 לנועה עבור עיצוב לוגו, תשלום בביט?"
def test_query_answer_revenue():
    assert render_query_answer(QueryType.TOTAL_REVENUE, {"period": "THIS_YEAR", "total": 42300.0}) \
        == "ההכנסות שלך השנה הן ₪42,300."

def test_confirmation_unknown_payment_method_no_keyerror():
    from app.utils.hebrew import build_confirmation_message
    msg = build_confirmation_message(IntentType.CREATE_RECEIPT,
        {"client_name": "נ", "amount": 50.0, "description": "x", "payment_method": "wire"})
    assert "wire" in msg  # off-enum value falls through, no KeyError

# backend/tests/test_chat_annual_report.py
from app.schemas.ai_commands import IntentType, ParsedUserCommand
from app.schemas.business import Business
from app.services import chat_service
from tests.test_report_precheck import seed_expense

class _AnnualStub:
    def parse_user_command(self, context, message):
        return (ParsedUserCommand(intent=IntentType.GENERATE_ANNUAL_REPORT,
                                  confidence=0.95, language="he", missing_fields=[]),
                None, "gpt-4.1-mini")
    def extract_expense(self, image_url):
        raise NotImplementedError

def _last_assistant_text(db, biz_id):
    msgs = db.collection("businesses").document(biz_id).collection("chatThreads") \
        .document("main").collection("messages").order_by("createdAt").stream()
    return [m.to_dict() for m in msgs if m.to_dict()["role"] == "assistant"][-1]["text"]

def test_annual_report_intent_answers_with_precheck_summary(db, make_business):
    biz = make_business()
    seed_expense(db, biz["id"], status="needs_review", category=None, imageUrl=None)
    business = Business.model_validate(biz)
    chat_service.handle_message(db, _AnnualStub(), business, "main", "צור דוח שנתי")
    text = _last_assistant_text(db, biz["id"])
    assert "הוצאות שדורשות בדיקה" in text and "/annual-report" in text

def test_annual_report_intent_all_clear(db, make_business):
    biz = make_business()
    chat_service.handle_message(db, _AnnualStub(), Business.model_validate(biz), "main", "דוח שנתי")
    assert "/annual-report" in _last_assistant_text(db, biz["id"])

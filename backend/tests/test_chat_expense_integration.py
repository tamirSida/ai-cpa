# backend/tests/test_chat_expense_integration.py
from app.schemas.ai_commands import ExpensePayload, IntentType, ParsedUserCommand
from app.services import aggregation_service, expense_service
from app.schemas.expense import ExpenseCreate
from app.utils.dates import year_bounds

def _cmd(**expense_kw):
    defaults = dict(supplier_name="Canva", amount=120.0, currency="ILS",
                    category="software", description="מנוי Canva",
                    business_use_percent=None, expense_date=None)
    defaults.update(expense_kw)
    return ParsedUserCommand(
        intent=IntentType.CREATE_EXPENSE, confidence=0.95, language="he",
        receipt=None, contact=None, query=None,
        expense=ExpensePayload(**defaults),
        missing_fields=[], requires_confirmation=True, user_facing_message=None, resolved_from_context=False)

def test_text_expense_confirm_creates_approved_expense(api, db, make_business, stub_parser):
    biz = make_business()
    stub_parser.queue_command(_cmd())
    r1 = api.post(f"/api/businesses/{biz['id']}/chat/message", json={"text": "תוסיף הוצאה של 120 שקל על Canva"})
    assert r1.status_code == 200                       # -> pending_confirmation
    r2 = api.post(f"/api/businesses/{biz['id']}/chat/message", json={"text": "אישור"})  # fast-path, no LLM
    assert r2.status_code == 200
    expenses = expense_service.list_expenses(db, biz["id"])
    assert len(expenses) == 1
    assert expenses[0].status == "approved" and expenses[0].amount == 120.0 and expenses[0].category == "software"

def test_chat_expense_without_category_lands_needs_review(api, db, make_business, stub_parser):
    biz = make_business()
    stub_parser.queue_command(_cmd(category=None))
    api.post(f"/api/businesses/{biz['id']}/chat/message", json={"text": "שילמתי 120 שקל למישהו"})
    api.post(f"/api/businesses/{biz['id']}/chat/message", json={"text": "כן"})
    assert expense_service.list_expenses(db, biz["id"])[0].status == "needs_review"

def test_total_expenses_approved_only_weighted(db, make_business):
    biz = make_business()
    expense_service.create_expense(db, biz["id"], ExpenseCreate(amount=100.0, category="software", expense_date="2026-03-01"), source="manual")                      # approved, 100%
    expense_service.create_expense(db, biz["id"], ExpenseCreate(amount=200.0, category="office", business_use_percent=50, expense_date="2026-04-01"), source="manual")  # approved, 50%
    expense_service.create_expense(db, biz["id"], ExpenseCreate(amount=500.0, expense_date="2026-05-01"), source="manual")                                            # needs_review -> excluded
    start, end = year_bounds(2026)
    assert aggregation_service.total_expenses(db, biz["id"], start, end) == 200.0   # 100 + 200*0.5
    assert aggregation_service.expenses_by_category(db, biz["id"], 2026) == {"software": 100.0, "office": 100.0}

# backend/tests/test_expense_schemas.py
from app.schemas.expense import Expense, ExpenseCreate

def test_expense_serializes_camel_case_with_defaults():
    exp = Expense(id="e1", business_id="b1", status="needs_review",
                  created_at="2026-06-13T10:00:00+03:00", updated_at="2026-06-13T10:00:00+03:00")
    data = exp.model_dump(by_alias=True)
    assert data["businessId"] == "b1"
    assert data["businessUsePercent"] == 100
    assert data["supplierName"] is None and data["currency"] == "ILS"

def test_create_accepts_camel_and_snake_and_plain_enum_values():
    a = ExpenseCreate(supplier_name="Canva", amount=120, category="software")
    b = ExpenseCreate.model_validate({"supplierName": "Canva", "amount": 120, "category": "software"})
    assert a == b and a.category == "software"  # use_enum_values -> plain str

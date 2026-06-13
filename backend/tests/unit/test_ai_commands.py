import pytest
from app.schemas import ai_commands as ac

WIRE_MODELS = [ac.TimeRange, ac.ReceiptPayload, ac.ContactPayload, ac.ExpensePayload,
               ac.QueryPayload, ac.ParsedUserCommand, ac.ExpenseExtraction]

def test_wire_models_have_no_non_none_defaults():
    # OpenAI strict structured outputs: every field required; only None defaults allowed (SDK strips them).
    for model in WIRE_MODELS:
        for name, field in model.model_fields.items():
            assert field.is_required() or field.default is None, f"{model.__name__}.{name} has non-None default"

def test_minimal_command_parses():
    cmd = ac.ParsedUserCommand.model_validate({"intent": "CREATE_RECEIPT",
        "receipt": {"client_name": "נועה", "amount": 2800, "description": "עיצוב לוגו"}})
    assert cmd.receipt.payment_method is None and cmd.missing_fields is None

def test_expense_extraction_category_enum():
    e = ac.ExpenseExtraction.model_validate({"supplier_name": "Canva", "amount": 120, "category": "software"})
    assert e.category == ac.ExpenseCategory.SOFTWARE

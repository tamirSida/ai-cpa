# backend/tests/test_expense_service.py
import pytest
from fastapi import HTTPException
from app.schemas.expense import ExpenseCreate, ExpensePatch
from app.services import expense_service

def _payload(**kw):
    base = {"supplier_name": "Canva", "amount": 120.0, "category": "software"}
    base.update(kw); return ExpenseCreate(**base)

def _ledger(db, biz_id):
    return [s.to_dict() for s in db.collection("businesses").document(biz_id).collection("ledgerEvents").stream()]

def test_manual_with_amount_and_category_is_approved(db, make_business):
    biz = make_business()
    exp = expense_service.create_expense(db, biz["id"], _payload(), source="manual")
    assert exp.status == "approved" and exp.amount == 120.0 and exp.business_use_percent == 100

def test_missing_category_needs_review(db, make_business):
    biz = make_business()
    exp = expense_service.create_expense(db, biz["id"], _payload(category=None), source="chat")
    assert exp.status == "needs_review"

def test_image_source_always_needs_review_even_when_complete(db, make_business):
    biz = make_business()
    exp = expense_service.create_expense(db, biz["id"], _payload(image_url="https://x/y.jpg",
        cloudinary_public_id="expenses/abc"), source="image")
    assert exp.status == "needs_review" and exp.cloudinary_public_id == "expenses/abc"

def test_create_writes_ledger_event_with_source(db, make_business):
    biz = make_business()
    expense_service.create_expense(db, biz["id"], _payload(), source="manual")
    events = _ledger(db, biz["id"])
    assert len(events) == 1 and events[0]["type"] == "expense_created"
    assert events[0]["amount"] == 120.0 and events[0]["metadata"]["source"] == "manual"

def test_business_use_percent_clamped_0_100(db, make_business):
    biz = make_business()
    assert expense_service.create_expense(db, biz["id"], _payload(business_use_percent=250), source="manual").business_use_percent == 100
    assert expense_service.create_expense(db, biz["id"], _payload(business_use_percent=-5), source="manual").business_use_percent == 0

def test_manual_without_amount_400(db, make_business):
    biz = make_business()
    with pytest.raises(HTTPException) as e:
        expense_service.create_expense(db, biz["id"], ExpenseCreate(supplier_name="Canva"), source="manual")
    assert e.value.status_code == 400 and e.value.detail["code"] == "missing_amount"

def test_approve_flips_status_and_logs(db, make_business):
    biz = make_business()
    exp = expense_service.create_expense(db, biz["id"], _payload(category=None), source="chat")
    out = expense_service.approve_expense(db, biz["id"], exp.id)
    assert out.status == "approved"
    assert {e["type"] for e in _ledger(db, biz["id"])} == {"expense_created", "expense_approved"}

def test_approve_twice_409(db, make_business):
    biz = make_business()
    exp = expense_service.create_expense(db, biz["id"], _payload(category=None), source="chat")
    expense_service.approve_expense(db, biz["id"], exp.id)
    with pytest.raises(HTTPException) as e:
        expense_service.approve_expense(db, biz["id"], exp.id)
    assert e.value.status_code == 409 and e.value.detail["code"] == "invalid_expense_status"

def test_approve_without_amount_422(db, make_business):
    biz = make_business()
    exp = expense_service.create_expense(db, biz["id"], _payload(amount=None, category=None,
        image_url="https://x/y.jpg", cloudinary_public_id="expenses/abc"), source="image")
    with pytest.raises(HTTPException) as e:
        expense_service.approve_expense(db, biz["id"], exp.id)
    assert e.value.status_code == 422 and e.value.detail["code"] == "missing_amount"

def test_reject_flips_status_and_logs(db, make_business):
    biz = make_business()
    exp = expense_service.create_expense(db, biz["id"], _payload(category=None), source="chat")
    out = expense_service.reject_expense(db, biz["id"], exp.id)
    assert out.status == "rejected"
    assert "expense_rejected" in {e["type"] for e in _ledger(db, biz["id"])}

def test_reject_non_needs_review_409(db, make_business):
    biz = make_business()
    exp = expense_service.create_expense(db, biz["id"], _payload(), source="manual")
    with pytest.raises(HTTPException) as e:
        expense_service.reject_expense(db, biz["id"], exp.id)
    assert e.value.status_code == 409 and e.value.detail["code"] == "invalid_expense_status"

def test_update_only_while_needs_review(db, make_business):
    biz = make_business()
    exp = expense_service.create_expense(db, biz["id"], _payload(), source="manual")
    with pytest.raises(HTTPException) as e:
        expense_service.update_expense(db, biz["id"], exp.id, ExpensePatch(amount=99.999))
    assert e.value.status_code == 409 and e.value.detail["code"] == "invalid_expense_status"

def test_update_applies_whitelist_and_rounds(db, make_business):
    biz = make_business()
    exp = expense_service.create_expense(db, biz["id"], _payload(category=None), source="chat")
    out = expense_service.update_expense(db, biz["id"], exp.id, ExpensePatch(amount=99.999, category="office"))
    assert out.amount == 100.0 and out.category == "office" and out.status == "needs_review"

def test_update_invalid_date_422(db, make_business):
    biz = make_business()
    exp = expense_service.create_expense(db, biz["id"], _payload(category=None), source="chat")
    with pytest.raises(HTTPException) as e:
        expense_service.update_expense(db, biz["id"], exp.id, ExpensePatch(expense_date="13/06/2026"))
    assert e.value.status_code == 422 and e.value.detail["code"] == "invalid_date"

def test_update_empty_patch_422(db, make_business):
    biz = make_business()
    exp = expense_service.create_expense(db, biz["id"], _payload(category=None), source="chat")
    with pytest.raises(HTTPException) as e:
        expense_service.update_expense(db, biz["id"], exp.id, ExpensePatch())
    assert e.value.status_code == 422 and e.value.detail["code"] == "no_updatable_fields"

def test_list_filters_status_and_year(db, make_business):
    biz = make_business()
    expense_service.create_expense(db, biz["id"], _payload(expense_date="2026-03-01"), source="manual")
    expense_service.create_expense(db, biz["id"], _payload(expense_date="2025-12-01"), source="manual")
    expense_service.create_expense(db, biz["id"], _payload(category=None, expense_date="2026-05-01"), source="chat")
    assert len(expense_service.list_expenses(db, biz["id"], status="approved")) == 2
    assert len(expense_service.list_expenses(db, biz["id"], year=2026)) == 2
    assert len(expense_service.list_expenses(db, biz["id"], status="approved", year=2026)) == 1

def test_approve_missing_id_404(db, make_business):
    biz = make_business()
    with pytest.raises(HTTPException) as e:
        expense_service.approve_expense(db, biz["id"], "nope")
    assert e.value.status_code == 404 and e.value.detail["code"] == "expense_not_found"

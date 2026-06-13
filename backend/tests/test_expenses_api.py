from app.schemas.expense import ExpenseCreate
from app.services import expense_service


def test_manual_create_201_camel_case(api, db, make_business):
    biz = make_business()
    r = api.post(f"/api/businesses/{biz['id']}/expenses",
                 json={"supplierName": "Canva", "amount": 120, "category": "software", "description": "מנוי"})
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "approved" and body["supplierName"] == "Canva"
    assert body["businessUsePercent"] == 100 and "supplier_name" not in body


def test_manual_create_missing_amount_400(api, make_business):
    biz = make_business()
    r = api.post(f"/api/businesses/{biz['id']}/expenses",
                 json={"supplierName": "Canva", "category": "software"})
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "missing_amount"


def test_manual_create_invalid_category_422(api, make_business):
    biz = make_business()
    r = api.post(f"/api/businesses/{biz['id']}/expenses",
                 json={"amount": 50, "category": "food"})
    assert r.status_code == 422


def test_manual_create_zero_amount_422(api, make_business):
    biz = make_business()
    r = api.post(f"/api/businesses/{biz['id']}/expenses",
                 json={"amount": 0})
    assert r.status_code == 422


def test_list_filters_by_status(api, db, make_business):
    biz = make_business()
    expense_service.create_expense(db, biz["id"], ExpenseCreate(supplier_name="A", amount=50, category="software"), source="manual")
    expense_service.create_expense(db, biz["id"], ExpenseCreate(supplier_name="B", amount=30), source="manual")
    r = api.get(f"/api/businesses/{biz['id']}/expenses?status=approved")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["status"] == "approved"


def test_list_invalid_status_422(api, make_business):
    biz = make_business()
    r = api.get(f"/api/businesses/{biz['id']}/expenses?status=pending")
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "invalid_status_filter"


def test_patch_needs_review_200(api, db, make_business):
    biz = make_business()
    expense = expense_service.create_expense(db, biz["id"], ExpenseCreate(supplier_name="X", amount=100), source="manual")
    r = api.patch(f"/api/businesses/{biz['id']}/expenses/{expense.id}",
                  json={"category": "office", "amount": 75.5})
    assert r.status_code == 200
    body = r.json()
    assert body["category"] == "office"
    assert body["amount"] == 75.5


def test_patch_approved_409(api, db, make_business):
    biz = make_business()
    expense = expense_service.create_expense(db, biz["id"], ExpenseCreate(supplier_name="X", amount=100, category="software"), source="manual")
    r = api.patch(f"/api/businesses/{biz['id']}/expenses/{expense.id}",
                  json={"amount": 200})
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "invalid_expense_status"


def test_patch_cannot_touch_status_or_image(api, db, make_business):
    biz = make_business()
    expense = expense_service.create_expense(db, biz["id"], ExpenseCreate(supplier_name="X", amount=100), source="manual")
    r = api.patch(f"/api/businesses/{biz['id']}/expenses/{expense.id}",
                  json={"status": "approved", "imageUrl": "https://evil", "category": "office"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "needs_review"
    assert body.get("imageUrl") is None


def test_approve_endpoint_200_then_409(api, db, make_business):
    biz = make_business()
    expense = expense_service.create_expense(db, biz["id"], ExpenseCreate(supplier_name="X", amount=100), source="manual")
    r1 = api.post(f"/api/businesses/{biz['id']}/expenses/{expense.id}/approve")
    assert r1.status_code == 200
    assert r1.json()["status"] == "approved"
    r2 = api.post(f"/api/businesses/{biz['id']}/expenses/{expense.id}/approve")
    assert r2.status_code == 409


def test_reject_endpoint_200(api, db, make_business):
    biz = make_business()
    expense = expense_service.create_expense(db, biz["id"], ExpenseCreate(supplier_name="X", amount=100), source="manual")
    r = api.post(f"/api/businesses/{biz['id']}/expenses/{expense.id}/reject")
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"


def test_other_owner_403(api, make_business):
    biz = make_business(ownerUserId="other-uid")
    r = api.get(f"/api/businesses/{biz['id']}/expenses")
    assert r.status_code == 403

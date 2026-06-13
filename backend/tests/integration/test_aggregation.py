# backend/tests/integration/test_aggregation.py
from datetime import date
from app.services import aggregation_service as agg
from app.schemas.business import Business

def _seed_receipt(db, bid, amount, issue_date, status="issued", client="נועה"):
    db.collection("businesses").document(bid).collection("receipts").document().set({
        "businessId": bid, "status": status, "amount": amount, "currency": "ILS",
        "issueDate": issue_date, "clientSnapshot": {"name": client}})

def test_total_revenue_filters_status_and_range(db, make_business):
    biz = make_business()
    _seed_receipt(db, biz["id"], 1000.0, "2026-02-01")
    _seed_receipt(db, biz["id"], 500.0, "2026-03-15")
    _seed_receipt(db, biz["id"], 999.0, "2026-03-15", status="draft")     # excluded
    _seed_receipt(db, biz["id"], 999.0, "2025-12-31")                      # out of range
    assert agg.total_revenue(db, biz["id"], date(2026, 1, 1), date(2026, 12, 31)) == 1500.0

def test_monthly_income_buckets(db, make_business):
    biz = make_business(); _seed_receipt(db, biz["id"], 1000.0, "2026-02-01"); _seed_receipt(db, biz["id"], 500.0, "2026-02-20")
    m = agg.monthly_income(db, biz["id"], 2026)
    assert m[2] == 1500.0 and m[1] == 0.0 and len(m) == 12

def test_client_revenue_exact_snapshot_name(db, make_business):
    biz = make_business(); _seed_receipt(db, biz["id"], 700.0, "2026-01-05", client="נועה")
    _seed_receipt(db, biz["id"], 50.0, "2026-01-06", client="דניאל")
    assert agg.client_revenue(db, biz["id"], "נועה") == 700.0

def test_receipts_count_and_threshold(db, make_business):
    biz = make_business(); _seed_receipt(db, biz["id"], 110000.0, "2026-01-05")
    assert agg.receipts_count(db, biz["id"], 2026) == 1
    ts = agg.threshold_status(db, Business.model_validate(biz), 2026)
    assert ts.total == 110000.0 and ts.limit == 120000.0 and ts.warning is True and ts.pct == 91.7

def test_expense_aggregations_empty_collections_return_zero(db, make_business):
    biz = make_business()
    assert agg.total_expenses(db, biz["id"], date(2026, 1, 1), date(2026, 12, 31)) == 0.0
    assert agg.expenses_by_category(db, biz["id"], 2026) == {}

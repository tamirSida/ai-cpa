# backend/tests/test_dashboard_api.py
from datetime import datetime, timedelta
import pytest
from app.utils.dates import IL_TZ, today_il
from tests.seeders import seed_expense, seed_receipt


def test_dashboard_full(api, db, make_business):
    today = today_il()
    year, this_month = today.year, today.month
    other_month = 1 if this_month != 1 else 2
    other_date = f"{year}-{other_month:02d}-15"
    now = datetime.now(IL_TZ)
    bid = make_business(phone="0501234567", email="tamir@example.com", address=None)["id"]

    r1 = seed_receipt(db, bid, seq=2, amount=1000.0, issue_date=today.isoformat(),
                      issued_at=now, pdf_url="https://res.cloudinary.com/d/raw/r1.pdf")
    r2 = seed_receipt(db, bid, seq=1, amount=500.5, issue_date=other_date,
                      issued_at=now - timedelta(days=30))                      # issued, no PDF
    seed_receipt(db, bid, seq=3, amount=999.0, issue_date=today.isoformat(),
                 issued_at=now - timedelta(days=1), status="cancelled")        # excluded everywhere
    seed_receipt(db, bid, seq=0, amount=50.0, issue_date=today.isoformat(), status="draft")

    e1 = seed_expense(db, bid, amount=200.0, status="approved", category="software",
                      expense_date=today.isoformat(), created_at=now - timedelta(days=3))
    e2 = seed_expense(db, bid, amount=100.0, status="approved", category="office",
                      expense_date=other_date, use_pct=50, created_at=now - timedelta(days=2))
    e3 = seed_expense(db, bid, amount=300.0, status="needs_review", created_at=now - timedelta(days=1))
    e4 = seed_expense(db, bid, amount=80.0, status="needs_review", created_at=now)

    res = api.get(f"/api/businesses/{bid}/dashboard")
    assert res.status_code == 200
    d = res.json()
    # totals: 1000 + 500.5 issued; expenses 200*100% + 100*50% = 250; profit = 1500.5 - 250
    assert d["totals"] == {"incomeThisYear": 1500.5, "incomeThisMonth": 1000.0,
                           "expensesThisYear": 250.0, "estimatedProfit": 1250.5}
    assert d["counts"] == {"receiptsCount": 2, "approvedExpensesCount": 2, "needsReviewCount": 2}
    assert d["threshold"]["total"] == 1500.5 and d["threshold"]["limit"] == 120000
    assert d["threshold"]["pct"] == pytest.approx(1500.5 / 120000 * 100, abs=0.1)
    assert d["threshold"]["warning"] is False
    monthly = {m["month"]: m["total"] for m in d["monthlyIncome"]}
    assert len(d["monthlyIncome"]) == 12 and set(monthly) == set(range(1, 13))
    assert monthly[this_month] == 1000.0 and monthly[other_month] == 500.5
    assert sum(monthly.values()) == 1500.5  # all other Asia/Jerusalem buckets are 0
    assert d["expensesByCategory"] == {"software": 200.0, "office": 50.0}
    assert [r["id"] for r in d["recentReceipts"]] == [r1, r2]  # issuedAt DESC
    assert d["recentReceipts"][0] == {"id": r1, "receiptNumber": "2026-0002", "clientName": "נועה",
                                      "amount": 1000.0, "issueDate": today.isoformat(),
                                      "pdfUrl": "https://res.cloudinary.com/d/raw/r1.pdf"}
    assert d["recentReceipts"][1]["pdfUrl"] is None
    assert [e["id"] for e in d["recentExpenses"]] == [e4, e3, e2, e1]  # createdAt DESC
    assert d["recentExpenses"][0] == {"id": e4, "supplierName": "Canva", "amount": 80.0,
                                      "category": None, "expenseDate": None, "status": "needs_review"}
    assert d["warnings"] == ["2 הוצאות ממתינות לבדיקה",
                             "חסרים פרטים בפרופיל העסק: כתובת",
                             "1 קבלות ללא קובץ PDF"]


def test_dashboard_threshold_warning(api, db, make_business):
    bid = make_business(address="הרצל 1", phone="0501234567", email="t@x.co")["id"]
    seed_receipt(db, bid, seq=1, amount=110000.0, issue_date=today_il().isoformat(),
                 issued_at=datetime.now(IL_TZ), pdf_url="https://res.cloudinary.com/d/raw/r.pdf")
    d = api.get(f"/api/businesses/{bid}/dashboard").json()
    assert d["threshold"]["warning"] is True
    assert len(d["warnings"]) == 1 and d["warnings"][0].startswith("הגעת ל-92% מתקרת עוסק פטור")


def test_dashboard_empty_business(api, db, make_business):
    bid = make_business(address="הרצל 1", phone="0501234567", email="t@x.co")["id"]
    d = api.get(f"/api/businesses/{bid}/dashboard").json()
    assert d["totals"] == {"incomeThisYear": 0.0, "incomeThisMonth": 0.0,
                           "expensesThisYear": 0.0, "estimatedProfit": 0.0}
    assert d["counts"] == {"receiptsCount": 0, "approvedExpensesCount": 0, "needsReviewCount": 0}
    assert {m["total"] for m in d["monthlyIncome"]} == {0.0}
    assert d["expensesByCategory"] == {} and d["recentReceipts"] == []
    assert d["recentExpenses"] == [] and d["warnings"] == []

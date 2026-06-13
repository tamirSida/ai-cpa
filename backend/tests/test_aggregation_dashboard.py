from datetime import datetime, timedelta
from app.services import aggregation_service
from app.utils.dates import IL_TZ, today_il
from tests.seeders import seed_expense, seed_receipt


def test_recent_receipts_issued_only_newest_first_limit(db, make_business):
    bid = make_business()["id"]
    now = datetime.now(IL_TZ)
    today = today_il().isoformat()
    ids = [seed_receipt(db, bid, seq=i, amount=100.0 * i, issue_date=today,
                        issued_at=now - timedelta(days=10 - i)) for i in range(1, 8)]
    seed_receipt(db, bid, seq=99, amount=1.0, issue_date=today, status="draft")
    seed_receipt(db, bid, seq=98, amount=1.0, issue_date=today, issued_at=now, status="cancelled")
    recents = aggregation_service.recent_receipts(db, bid, limit=5)
    assert [r["id"] for r in recents] == list(reversed(ids))[:5]
    assert all(r["status"] == "issued" for r in recents)


def test_dashboard_counts_and_missing_pdfs(db, make_business):
    bid = make_business()["id"]
    now, year = datetime.now(IL_TZ), today_il().year
    today = today_il().isoformat()
    seed_receipt(db, bid, seq=1, amount=100.0, issue_date=today, issued_at=now, pdf_url="https://x/r1.pdf")
    seed_receipt(db, bid, seq=2, amount=200.0, issue_date=today, issued_at=now)  # missing PDF
    e1 = seed_expense(db, bid, amount=50.0, status="approved", category="software", expense_date=today)
    seed_expense(db, bid, amount=60.0, status="approved", category="office", expense_date=f"{year - 1}-05-01")
    e3 = seed_expense(db, bid, amount=70.0, status="needs_review", created_at=now + timedelta(hours=1))
    assert aggregation_service.approved_expenses_count(db, bid, year) == 1
    assert aggregation_service.needs_review_count(db, bid) == 1
    assert aggregation_service.receipts_missing_pdf_count(db, bid) == 1
    assert [e["id"] for e in aggregation_service.recent_expenses(db, bid, limit=5)][0] == e3
    assert e1 in [e["id"] for e in aggregation_service.recent_expenses(db, bid, limit=5)]

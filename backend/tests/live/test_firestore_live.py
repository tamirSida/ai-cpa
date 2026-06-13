"""Live Firestore smoke — proves the deployed composite indexes serve the app's actual
compound queries. The emulator ignores indexes, so this is the only place a missing or
wrong index (FAILED_PRECONDITION) would surface before production."""

from datetime import date, datetime, timezone

from app.services import aggregation_service as agg


def test_composite_indexes_serve_app_queries(live_db):
    bid = "zzz_live_pytest_index"
    biz = live_db.collection("businesses").document(bid)
    receipts, expenses = biz.collection("receipts"), biz.collection("expenses")
    biz.set({"id": bid, "businessName": "LIVE PYTEST DELETE ME"})
    receipts.document("r1").set({
        "status": "issued", "issueDate": "2026-03-01", "amount": 2800.0,
        "clientSnapshot": {"name": "נועה"},
        "issuedAt": datetime(2026, 3, 1, tzinfo=timezone.utc), "pdfUrl": "http://x/p.pdf",
    })
    expenses.document("e1").set({
        "status": "approved", "expenseDate": "2026-03-05", "amount": 120.0,
        "businessUsePercent": 100, "category": "software",
    })
    try:
        # Each call below runs a compound query backed by one of the deployed composite
        # indexes; a missing index raises google.api_core.exceptions.FailedPrecondition.
        assert agg.total_revenue(live_db, bid, date(2026, 1, 1), date(2026, 12, 31)) == 2800.0   # status+issueDate
        assert agg.client_revenue(live_db, bid, "נועה") == 2800.0                                # status+clientSnapshot.name
        assert len(agg.recent_receipts(live_db, bid)) == 1                                       # status+issuedAt DESC
        assert agg.total_expenses(live_db, bid, date(2026, 1, 1), date(2026, 12, 31)) == 120.0   # status+expenseDate
        assert agg.approved_expenses_count(live_db, bid, 2026) == 1                              # status+expenseDate
    finally:
        receipts.document("r1").delete()
        expenses.document("e1").delete()
        biz.delete()

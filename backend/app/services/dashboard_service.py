# backend/app/services/dashboard_service.py
from concurrent.futures import ThreadPoolExecutor

from google.cloud import firestore
from app.schemas.business import Business
from app.schemas.dashboard import (DashboardCounts, DashboardResponse, DashboardTotals,
                                   MonthlyIncomeEntry, RecentExpense, RecentReceipt, ThresholdOut)
from app.services import aggregation_service
from app.utils.dates import month_bounds, today_il, year_bounds
from app.utils.money import format_ils, round_ils

_PROFILE_FIELD_LABELS = [("address", "כתובת"), ("phone", "טלפון"), ("email", "אימייל")]


def build_warnings(business: Business, needs_review_count: int,
                   threshold: ThresholdOut, missing_pdf_count: int) -> list[str]:
    warnings: list[str] = []
    if needs_review_count > 0:
        warnings.append(f"{needs_review_count} הוצאות ממתינות לבדיקה")
    missing = [label for attr, label in _PROFILE_FIELD_LABELS if not getattr(business, attr, None)]
    if missing:
        warnings.append("חסרים פרטים בפרופיל העסק: " + ", ".join(missing))
    if threshold.warning:
        warnings.append(
            f"הגעת ל-{threshold.pct:.0f}% מתקרת עוסק פטור "
            f"({format_ils(threshold.total)} מתוך {format_ils(threshold.limit)})"
        )
    if missing_pdf_count > 0:
        warnings.append(f"{missing_pdf_count} קבלות ללא קובץ PDF")
    return warnings


def get_dashboard(db: firestore.Client, business: Business) -> DashboardResponse:
    today = today_il()
    year, month = today.year, today.month
    y_start, y_end = year_bounds(year)
    m_start, m_end = month_bounds(year, month)

    bid = business.id
    agg = aggregation_service
    # Each aggregation issues its own Firestore round-trip(s); they are independent reads and the
    # sync Firestore client is thread-safe, so fan them out concurrently. Wall-clock drops from
    # sum-of-queries to ~the slowest single query — the dominant cost when the DB is in a remote region.
    jobs = {
        "income_year": lambda: agg.total_revenue(db, bid, y_start, y_end),
        "income_month": lambda: agg.total_revenue(db, bid, m_start, m_end),
        "expenses_year": lambda: agg.total_expenses(db, bid, y_start, y_end),
        "ts": lambda: agg.threshold_status(db, business, year),
        "monthly": lambda: agg.monthly_income(db, bid, year),
        "needs_review": lambda: agg.needs_review_count(db, bid),
        "missing_pdf": lambda: agg.receipts_missing_pdf_count(db, bid),
        "receipts_count": lambda: agg.receipts_count(db, bid, year),
        "approved_count": lambda: agg.approved_expenses_count(db, bid, year),
        "by_category": lambda: agg.expenses_by_category(db, bid, year),
        "recent_receipts": lambda: agg.recent_receipts(db, bid, limit=5),
        "recent_expenses": lambda: agg.recent_expenses(db, bid, limit=5),
    }
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        futures = {key: pool.submit(fn) for key, fn in jobs.items()}
        r = {key: fut.result() for key, fut in futures.items()}   # re-raises any aggregation error

    income_year, expenses_year, monthly = r["income_year"], r["expenses_year"], r["monthly"]
    ts = r["ts"]
    threshold = ThresholdOut(total=ts.total, limit=ts.limit, pct=ts.pct, warning=ts.warning)

    return DashboardResponse(
        totals=DashboardTotals(
            income_this_year=round_ils(income_year),
            income_this_month=round_ils(r["income_month"]),
            # deductible (business_use_percent-weighted) total; the frontend labels it
            # "הוצאות מוכרות" so it's never mistaken for gross spend (see Task 4.5 review)
            expenses_this_year=round_ils(expenses_year),
            estimated_profit=round_ils(income_year - expenses_year),
        ),
        counts=DashboardCounts(
            receipts_count=r["receipts_count"],
            approved_expenses_count=r["approved_count"],
            needs_review_count=r["needs_review"],
        ),
        threshold=threshold,
        monthly_income=[MonthlyIncomeEntry(month=m, total=round_ils(monthly.get(m, 0.0)))
                        for m in range(1, 13)],
        expenses_by_category={k: round_ils(v) for k, v in r["by_category"].items()},
        recent_receipts=[RecentReceipt(id=rr["id"], receipt_number=rr["receiptNumber"],
                                       client_name=rr["clientSnapshot"]["name"], amount=rr["amount"],
                                       issue_date=rr["issueDate"], pdf_url=rr.get("pdfUrl"))
                         for rr in r["recent_receipts"]],
        recent_expenses=[RecentExpense(id=e["id"], supplier_name=e.get("supplierName"),
                                       amount=e.get("amount"), category=e.get("category"),
                                       expense_date=e.get("expenseDate"), status=e["status"])
                         for e in r["recent_expenses"]],
        warnings=build_warnings(business, r["needs_review"], threshold, r["missing_pdf"]),
    )

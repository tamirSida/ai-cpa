# backend/app/services/dashboard_service.py
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

    income_year = aggregation_service.total_revenue(db, business.id, y_start, y_end)
    income_month = aggregation_service.total_revenue(db, business.id, m_start, m_end)
    expenses_year = aggregation_service.total_expenses(db, business.id, y_start, y_end)
    ts = aggregation_service.threshold_status(db, business, year)
    threshold = ThresholdOut(total=ts.total, limit=ts.limit, pct=ts.pct, warning=ts.warning)
    monthly = aggregation_service.monthly_income(db, business.id, year)
    needs_review = aggregation_service.needs_review_count(db, business.id)
    missing_pdf = aggregation_service.receipts_missing_pdf_count(db, business.id)

    return DashboardResponse(
        totals=DashboardTotals(
            income_this_year=round_ils(income_year),
            income_this_month=round_ils(income_month),
            # deductible (business_use_percent-weighted) total; the frontend labels it
            # "הוצאות מוכרות" so it's never mistaken for gross spend (see Task 4.5 review)
            expenses_this_year=round_ils(expenses_year),
            estimated_profit=round_ils(income_year - expenses_year),
        ),
        counts=DashboardCounts(
            receipts_count=aggregation_service.receipts_count(db, business.id, year),
            approved_expenses_count=aggregation_service.approved_expenses_count(db, business.id, year),
            needs_review_count=needs_review,
        ),
        threshold=threshold,
        monthly_income=[MonthlyIncomeEntry(month=m, total=round_ils(monthly.get(m, 0.0)))
                        for m in range(1, 13)],
        expenses_by_category={k: round_ils(v) for k, v in
                              aggregation_service.expenses_by_category(db, business.id, year).items()},
        recent_receipts=[RecentReceipt(id=r["id"], receipt_number=r["receiptNumber"],
                                       client_name=r["clientSnapshot"]["name"], amount=r["amount"],
                                       issue_date=r["issueDate"], pdf_url=r.get("pdfUrl"))
                         for r in aggregation_service.recent_receipts(db, business.id, limit=5)],
        recent_expenses=[RecentExpense(id=e["id"], supplier_name=e.get("supplierName"),
                                       amount=e.get("amount"), category=e.get("category"),
                                       expense_date=e.get("expenseDate"), status=e["status"])
                         for e in aggregation_service.recent_expenses(db, business.id, limit=5)],
        warnings=build_warnings(business, needs_review, threshold, missing_pdf),
    )

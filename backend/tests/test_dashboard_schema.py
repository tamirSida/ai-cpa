from app.schemas.dashboard import (
    DashboardCounts, DashboardResponse, DashboardTotals,
    MonthlyIncomeEntry, RecentExpense, RecentReceipt, ThresholdOut,
)


def test_dashboard_response_serializes_camel_case():
    resp = DashboardResponse(
        totals=DashboardTotals(income_this_year=1500.5, income_this_month=1000.0,
                               expenses_this_year=250.0, estimated_profit=1250.5),
        counts=DashboardCounts(receipts_count=2, approved_expenses_count=2, needs_review_count=1),
        threshold=ThresholdOut(total=1500.5, limit=120000, pct=1.3, warning=False),
        monthly_income=[MonthlyIncomeEntry(month=m, total=0.0) for m in range(1, 13)],
        expenses_by_category={"software": 200.0},
        recent_receipts=[RecentReceipt(id="r1", receipt_number="2026-0001", client_name="נועה",
                                       amount=1000.0, issue_date="2026-06-13", pdf_url=None)],
        recent_expenses=[RecentExpense(id="e1", supplier_name=None, amount=80.0,
                                       category=None, expense_date=None, status="needs_review")],
        warnings=["1 הוצאות ממתינות לבדיקה"],
    )
    data = resp.model_dump(by_alias=True)
    assert set(data) == {"totals", "counts", "threshold", "monthlyIncome", "expensesByCategory",
                         "recentReceipts", "recentExpenses", "warnings"}
    assert data["totals"] == {"incomeThisYear": 1500.5, "incomeThisMonth": 1000.0,
                              "expensesThisYear": 250.0, "estimatedProfit": 1250.5}
    assert data["counts"] == {"receiptsCount": 2, "approvedExpensesCount": 2, "needsReviewCount": 1}
    assert data["recentReceipts"][0]["receiptNumber"] == "2026-0001"
    assert data["recentReceipts"][0]["pdfUrl"] is None
    assert len(data["monthlyIncome"]) == 12 and data["monthlyIncome"][0] == {"month": 1, "total": 0.0}

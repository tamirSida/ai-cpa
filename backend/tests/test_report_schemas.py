from datetime import datetime
from app.schemas.report import AnnualReport, PrecheckResult

def test_precheck_result_serializes_camel_case():
    r = PrecheckResult(year=2026, expenses_needing_review=["e1"], expenses_missing_images=[],
                       uncategorized_expenses=[], receipts_missing_pdf=["2026-0003"], cancelled_receipts=[],
                       missing_business_fields=["address"], total_revenue=42300.0,
                       threshold_warning=False, issues_count=3)
    d = r.model_dump(by_alias=True)
    assert d["expensesNeedingReview"] == ["e1"] and d["receiptsMissingPdf"] == ["2026-0003"]

def test_annual_report_accepts_firestore_camel_dict():
    m = AnnualReport.model_validate({"id": "2026", "businessId": "b1", "year": 2026,
        "totalIncome": 1.0, "totalExpenses": 0.0, "estimatedProfit": 1.0,
        "warnings": [], "generatedAt": datetime(2026, 6, 13)})
    assert m.business_id == "b1"

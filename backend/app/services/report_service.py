# backend/app/services/report_service.py
from app.schemas.business import Business
from app.schemas.report import PrecheckResult
from app.services import aggregation_service, expense_service, receipt_service

_PROFILE_FIELDS = [("business_name", "businessName"), ("owner_name", "ownerName"),
                   ("business_id_number", "businessIdNumber"), ("address", "address"),
                   ("phone", "phone"), ("email", "email")]

def precheck(db, business: Business, year: int) -> PrecheckResult:
    # Expenses: a needs_review item is a GLOBAL readiness blocker — it usually has no
    # expenseDate yet (extraction pending), so a year filter would silently drop the exact
    # population that must be cleared. Scope to "in the report year OR still needs_review".
    all_expenses = expense_service.list_expenses(db, business.id)
    expenses = [e for e in all_expenses
                if (e.expense_date or "").startswith(f"{year}-") or e.status == "needs_review"]
    receipts = receipt_service.list_receipts(db, business.id, year=year)  # issued receipts always have issueDate
    needing_review = [e.id for e in expenses if e.status == "needs_review"]
    missing_images = [e.id for e in expenses if e.status in ("approved", "needs_review") and not e.image_url]
    uncategorized = [e.id for e in expenses if e.status != "rejected" and not e.category]
    missing_pdf = [r.receipt_number for r in receipts if r.status == "issued" and not r.pdf_url]
    cancelled = [r.receipt_number for r in receipts if r.status == "cancelled"]
    missing_profile = [camel for attr, camel in _PROFILE_FIELDS if not getattr(business, attr, None)]
    ts = aggregation_service.threshold_status(db, business, year)
    lists = [needing_review, missing_images, uncategorized, missing_pdf, cancelled, missing_profile]
    return PrecheckResult(year=year, expenses_needing_review=needing_review,
                          expenses_missing_images=missing_images, uncategorized_expenses=uncategorized,
                          receipts_missing_pdf=missing_pdf, cancelled_receipts=cancelled,
                          missing_business_fields=missing_profile, total_revenue=ts.total,
                          threshold_warning=ts.warning, issues_count=sum(len(x) for x in lists))

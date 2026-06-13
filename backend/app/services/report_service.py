# backend/app/services/report_service.py
import csv
import io

from app.schemas.business import Business
from app.schemas.report import PrecheckResult
from app.services import aggregation_service, expense_service, receipt_service
from app.utils.money import round_ils

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

def _csv_bytes(header: list[str], rows: list[list]) -> bytes:
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(header); w.writerows(rows)
    return out.getvalue().encode("utf-8-sig")   # BOM => Excel opens Hebrew correctly

def build_income_csv(receipts) -> bytes:
    rows = [[r.receipt_number, r.issue_date, r.client_snapshot.name, r.description,
             r.payment_method, r.amount, r.status]
            for r in sorted(receipts, key=lambda r: r.sequence_number or 0)]
    return _csv_bytes(["receiptNumber", "issueDate", "clientName", "description",
                       "paymentMethod", "amount", "status"], rows)

def build_expenses_csv(expenses) -> bytes:
    rows = []
    for e in sorted(expenses, key=lambda e: e.expense_date or ""):
        pct = e.business_use_percent if e.business_use_percent is not None else 100
        deductible = round_ils(e.amount * pct / 100) if e.amount is not None else ""
        rows.append([e.expense_date or "", e.supplier_name or "", e.category or "", e.description or "",
                     e.amount if e.amount is not None else "", pct, deductible, e.status,
                     "yes" if e.image_url else "no"])
    return _csv_bytes(["expenseDate", "supplierName", "category", "description", "amount",
                       "businessUsePercent", "deductibleAmount", "status", "hasImage"], rows)

def build_clients_csv(clients) -> bytes:
    rows = [[c.name, c.company_name or "", c.tax_id or "", c.phone or "", c.email or ""]
            for c in sorted(clients, key=lambda c: c.name)]
    return _csv_bytes(["name", "companyName", "taxId", "phone", "email"], rows)

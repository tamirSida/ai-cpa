# backend/app/services/report_service.py
import csv
import io
import logging

logger = logging.getLogger(__name__)

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

import zipfile
from concurrent.futures import ThreadPoolExecutor
import httpx
from app.services import client_service, ledger_service
from app.services.cloudinary_service import fetch_asset
from app.services.pdf_service import render_pdf
from app.utils.dates import now_il, year_bounds
from app.utils.money import format_ils, round_ils

HEBREW_MONTHS = ["ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
                 "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר"]
_IMG_EXTS = ("jpg", "jpeg", "png", "webp", "pdf")

def _fetch_assets(jobs: list[tuple[str, str]]) -> tuple[dict[str, bytes], list[str]]:
    results: dict[str, bytes] = {}; failures: list[str] = []
    with httpx.Client(timeout=20.0) as client, ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(fetch_asset, url, client): member for member, url in jobs}
        for fut, member in futures.items():
            try:
                results[member] = fut.result()
            except Exception:
                failures.append(member)
    return results, failures

def generate_zip(db, business: Business, year: int) -> io.BytesIO:
    check = precheck(db, business, year)
    receipts = [r for r in receipt_service.list_receipts(db, business.id, year=year)
                if r.status in ("issued", "cancelled")]          # drafts excluded; status column disambiguates
    expenses = [e for e in expense_service.list_expenses(db, business.id, year=year)
                if e.status in ("approved", "needs_review")]
    clients = client_service.list_clients(db, business.id)
    start, end = year_bounds(year)
    total_income = aggregation_service.total_revenue(db, business.id, start, end)
    total_expenses = aggregation_service.total_expenses(db, business.id, start, end)
    estimated_profit = round_ils(total_income - total_expenses)
    monthly = aggregation_service.monthly_income(db, business.id, year)
    by_cat = aggregation_service.expenses_by_category(db, business.id, year)
    summary_pdf = render_pdf("report_summary.html", {
        "year": year,
        "business": {"businessName": business.business_name, "ownerName": business.owner_name,
                     "businessIdNumber": business.business_id_number},
        "total_income": format_ils(total_income), "total_expenses": format_ils(total_expenses),
        "estimated_profit": format_ils(estimated_profit),
        "monthly": [{"label": HEBREW_MONTHS[m - 1], "amount": format_ils(monthly.get(m, 0.0))}
                    for m in range(1, 13)],
        "categories": [{"label": k, "amount": format_ils(v)} for k, v in sorted(by_cat.items())]})
    jobs = [(f"receipt_pdfs/{r.receipt_number}.pdf", r.pdf_url)
            for r in receipts if r.status == "issued" and r.pdf_url]
    for e in expenses:
        if e.image_url:
            ext = e.image_url.rsplit(".", 1)[-1].lower()
            jobs.append((f"expense_images/{e.id}.{ext if ext in _IMG_EXTS else 'jpg'}", e.image_url))
    assets, fetch_failures = _fetch_assets(jobs)
    sections = [{"title": t, "items": items} for t, items in [
        ("הוצאות שדורשות בדיקה", check.expenses_needing_review),
        ("הוצאות ללא קבלה מצולמת", check.expenses_missing_images),
        ("הוצאות ללא קטגוריה", check.uncategorized_expenses),
        ("קבלות ללא PDF", check.receipts_missing_pdf),
        ("קבלות מבוטלות", check.cancelled_receipts),
        ("פרטי עסק חסרים", check.missing_business_fields),
        ("קבצים שלא הורדו לחבילה", fetch_failures)] if items]
    missing_pdf = render_pdf("missing_items.html",
                             {"year": year, "sections": sections, "all_clear": not sections})
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("income.csv", build_income_csv(receipts))
        zf.writestr("expenses.csv", build_expenses_csv(expenses))
        zf.writestr("clients.csv", build_clients_csv(clients))
        zf.writestr("summary.pdf", summary_pdf)
        zf.writestr("missing_items.pdf", missing_pdf)
        for member, data in assets.items():
            zf.writestr(member, data)
    buf.seek(0)
    warnings = ([f"{check.issues_count} פריטים חסרים או דורשים בדיקה"] if check.issues_count else []) \
        + (["מתקרב לתקרת עוסק פטור"] if check.threshold_warning else []) \
        + [f"קובץ לא הורד: {m}" for m in fetch_failures]
    # Best-effort audit writes: the ZIP is already assembled, so a transient Firestore failure
    # here must NOT deny the user their year-end package. Log and still return the ZIP.
    try:
        db.collection("businesses").document(business.id).collection("annualReports") \
            .document(str(year)).set({"id": str(year), "businessId": business.id, "year": year,
                                      "totalIncome": total_income, "totalExpenses": total_expenses,
                                      "estimatedProfit": estimated_profit, "warnings": warnings,
                                      "generatedAt": now_il()})
        ledger_service.record_event(db, business.id, type="annual_report_generated",
                                    entity_type="annual_report", entity_id=str(year),
                                    metadata={"warnings": warnings})
    except Exception:
        logger.exception("annual report metadata/ledger write failed for business %s year %s",
                         business.id, year)
    return buf

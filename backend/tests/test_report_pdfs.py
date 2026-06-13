# backend/tests/test_report_pdfs.py
import io
from pypdf import PdfReader
from app.services.pdf_service import render_pdf

def _text(pdf: bytes) -> str:
    return "".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf)).pages)

def test_summary_pdf_contains_business_totals_and_months():
    ctx = {"year": 2026,
           "business": {"businessName": "סטודיו תמיר", "ownerName": "תמיר", "businessIdNumber": "123456789"},
           "total_income": "₪42,300.00", "total_expenses": "₪1,200.00", "estimated_profit": "₪41,100.00",
           "monthly": [{"label": "ינואר", "amount": "₪42,300.00"}] ,
           "categories": [{"label": "software", "amount": "₪1,200.00"}]}
    text = _text(render_pdf("report_summary.html", ctx))
    assert "סטודיו תמיר" in text and "42,300.00" in text and "ינואר" in text

def test_missing_items_pdf_lists_findings():
    ctx = {"year": 2026, "sections": [
        {"title": "הוצאות שדורשות בדיקה", "items": ["Canva — ₪120.00 (2026-02-10)"]},
        {"title": "קבלות ללא PDF", "items": ["2026-0002"]}], "all_clear": False}
    text = _text(render_pdf("missing_items.html", ctx))
    assert "הוצאות שדורשות בדיקה" in text and "2026-0002" in text

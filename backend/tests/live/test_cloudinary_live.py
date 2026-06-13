"""Live Cloudinary smokes — real upload, delivery (validates the "PDF and ZIP files
delivery" account setting), and the render -> upload -> fetch chain. The main suite
monkeypatches all of these."""

import cloudinary.uploader

from app.services.cloudinary_service import fetch_asset, upload_pdf
from app.services.pdf_service import render_pdf

# Known-good context for report_summary.html (mirrors report_service.generate_zip).
_SUMMARY_CTX = {
    "year": 2026,
    "business": {"businessName": "סטודיו בדיקה", "ownerName": "תמיר", "businessIdNumber": "123456789"},
    "total_income": "₪2,800.00",
    "total_expenses": "₪120.00",
    "estimated_profit": "₪2,680.00",
    "monthly": [{"label": "מרץ", "amount": "₪2,800.00"}],
    "categories": [{"label": "software", "amount": "₪120.00"}],
}


def _destroy(public_id: str) -> None:
    try:
        cloudinary.uploader.destroy(public_id, resource_type="raw")
    except Exception:
        pass


def test_pdf_upload_deliver_destroy(cloudinary_cfg):
    pid = "smoke_test/live_pytest_roundtrip.pdf"
    data = b"%PDF-1.7 live pytest roundtrip\n%%EOF\n"
    _destroy(pid)  # upload_pdf uses overwrite=False; ensure a clean slate
    res = upload_pdf(data, pid)
    try:
        assert res.secure_url.startswith("https://")
        # delivery returns the exact bytes only when "PDF and ZIP files delivery" is enabled
        assert fetch_asset(res.secure_url) == data
    finally:
        _destroy(res.public_id)


def test_full_render_upload_fetch_chain(cloudinary_cfg):
    pdf = render_pdf("report_summary.html", _SUMMARY_CTX)  # real WeasyPrint Hebrew RTL PDF
    assert pdf[:4] == b"%PDF"
    pid = "smoke_test/live_pytest_summary.pdf"
    _destroy(pid)
    res = upload_pdf(pdf, pid)
    try:
        fetched = fetch_asset(res.secure_url)
        assert fetched[:4] == b"%PDF"
        assert len(fetched) == len(pdf)
    finally:
        _destroy(res.public_id)

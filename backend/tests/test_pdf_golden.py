import io
from pypdf import PdfReader
from app.services.pdf_service import render_pdf

CTX = {"business": {"businessName": "סטודיו תמיר", "ownerName": "תמיר סידה",
                    "businessIdNumber": "300123456", "address": "תל אביב",
                    "phone": "050-1234567", "email": "tamir@example.com"},
       "receipt": {"receiptNumber": "2026-0007", "issueDate": "2026-06-13", "amount": 2800.0,
                   "paymentMethod": "bit", "description": "עיצוב לוגו",
                   "clientSnapshot": {"name": "נועה גולן", "taxId": "200999888"}}}

def test_receipt_pdf_golden():
    pdf = render_pdf("receipt.html", CTX)
    assert pdf[:5] == b"%PDF-"
    text = PdfReader(io.BytesIO(pdf)).pages[0].extract_text()
    name = "נועה גולן"
    assert name in text or name[::-1] in text  # pypdf may extract RTL runs in visual order
    assert "2,800" in text and "2026-0007" in text

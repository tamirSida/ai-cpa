import io
from pypdf import PdfReader
from app.services.pdf_service import render_pdf

BIZ = {"businessName": "סטודיו תמיר", "ownerName": "תמיר סידה", "businessIdNumber": "300123456",
       "address": "תל אביב", "phone": "050-1234567", "email": "tamir@example.com",
       "bankName": "דיסקונט", "bankBranch": "125", "bankAccount": "118863403"}

def _text(ctx):
    pdf = render_pdf("receipt.html", ctx)
    assert pdf[:5] == b"%PDF-"
    return PdfReader(io.BytesIO(pdf)).pages[0].extract_text()

def test_receipt_pdf_labels_and_total():
    ctx = {"business": BIZ, "signed": True,
           "receipt": {"receiptNumber": "2026-0007", "issueDate": "2026-06-13", "amount": 2800.0,
                       "paymentMethod": "bit", "description": "עיצוב לוגו",
                       "clientSnapshot": {"name": "נועה גולן", "taxId": "200999888"}}}
    text = _text(ctx)
    for needle in ("מקור", "מסמך ממוחשב", "2,800", "2026-0007"):
        assert needle in text or needle[::-1] in text

def test_receipt_pdf_check_details_shown():
    ctx = {"business": BIZ, "signed": True,
           "receipt": {"receiptNumber": "2026-0008", "issueDate": "2026-06-13", "amount": 500.0,
                       "paymentMethod": "check", "description": "שיעור",
                       "checkDetails": {"number": "55", "bank": "דיסקונט", "branch": "125", "dueDate": "2026-07-01"},
                       "clientSnapshot": {"name": "נועה"}}}
    text = _text(ctx)
    assert "55" in text and ("2026-07-01" in text or "2026-07-01"[::-1] in text)

def test_receipt_pdf_transfer_shows_business_bank():
    ctx = {"business": BIZ, "signed": True,
           "receipt": {"receiptNumber": "2026-0009", "issueDate": "2026-06-13", "amount": 500.0,
                       "paymentMethod": "bank_transfer", "description": "שיעור",
                       "clientSnapshot": {"name": "נועה"}}}
    assert "118863403" in _text(ctx)

def test_receipt_pdf_unsigned_shows_handsign_note():
    ctx = {"business": BIZ, "signed": False,
           "receipt": {"receiptNumber": "2026-0010", "issueDate": "2026-06-13", "amount": 80.0,
                       "paymentMethod": "cash", "description": "שיעור", "clientSnapshot": {"name": "נועה"}}}
    text = _text(ctx)
    assert "ידנית" in text or "ידנית"[::-1] in text

def test_receipt_pdf_unknown_payment_method_no_crash():
    ctx = {"business": BIZ, "signed": False,
           "receipt": {"receiptNumber": "2026-0011", "issueDate": "2026-06-13", "amount": 80.0,
                       "paymentMethod": "wire", "description": "x", "clientSnapshot": {"name": "נועה"}}}
    assert render_pdf("receipt.html", ctx)[:5] == b"%PDF-"

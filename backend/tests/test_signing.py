import io

from app.core.config import get_settings
from app.services import signing_service
from app.services.pdf_service import render_pdf
from scripts.gen_signing_cert import build_p12

_CTX = {
    "business": {"businessName": "עסק", "ownerName": "תמיר", "businessIdNumber": "300123456"},
    "receipt": {
        "receiptNumber": "2026-0001",
        "issueDate": "2026-05-01",
        "amount": 100.0,
        "paymentMethod": "bank_transfer",
        "description": "שיעור",
        "clientSnapshot": {"name": "נועה"},
    },
    "signed": True,
}


def test_is_signable_payment():
    assert signing_service.is_signable_payment("bank_transfer")
    assert signing_service.is_signable_payment("check")
    assert not signing_service.is_signable_payment("cash")
    assert not signing_service.is_signable_payment("other")


def test_unconfigured_is_false(monkeypatch):
    monkeypatch.setenv("RECEIPT_SIGNING_P12_PASSWORD", "")
    get_settings.cache_clear()
    assert signing_service.is_configured() is False
    get_settings.cache_clear()


def test_sign_pdf_embeds_signature(tmp_path, monkeypatch):
    p12 = tmp_path / "s.p12"
    p12.write_bytes(build_p12("AI Bookkeeper Test", "pw", years=2))
    monkeypatch.setenv("RECEIPT_SIGNING_P12_PATH", str(p12))
    monkeypatch.setenv("RECEIPT_SIGNING_P12_PASSWORD", "pw")
    get_settings.cache_clear()
    assert signing_service.is_configured() is True
    pdf = render_pdf("receipt.html", _CTX)
    signed = signing_service.sign_pdf(pdf)
    assert signed[:5] == b"%PDF-" and len(signed) > len(pdf)
    # assert exactly one embedded signature — adapt the reader import to the installed pyHanko version:
    from pyhanko.pdf_utils.reader import PdfFileReader

    assert len(PdfFileReader(io.BytesIO(signed)).embedded_signatures) == 1
    get_settings.cache_clear()

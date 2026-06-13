from app.schemas.business import Business
from app.schemas.receipt import ReceiptDraftCreate
from app.services import receipt_service

def _setup(monkeypatch):
    calls = {"signed": [], "ctx_signed": []}
    monkeypatch.setattr(receipt_service.signing_service, "is_configured", lambda: True)
    monkeypatch.setattr(receipt_service, "render_pdf",
                        lambda name, ctx: calls["ctx_signed"].append(ctx["signed"]) or b"%PDF-1.7 x")
    def fake_sign(pdf):
        calls["signed"].append(True); return pdf + b"-signed"
    monkeypatch.setattr(receipt_service.signing_service, "sign_pdf", fake_sign)
    from app.services.cloudinary_service import UploadResult
    monkeypatch.setattr(receipt_service, "upload_pdf",
                        lambda data, public_id: UploadResult(secure_url="https://x/p.pdf", public_id=public_id))
    return calls

def test_transfer_is_signed(db, make_business, monkeypatch):
    calls = _setup(monkeypatch)
    business = Business.model_validate(make_business())
    d = receipt_service.create_draft(db, business, ReceiptDraftCreate(
        client_name="נועה", amount=100.0, description="שיעור", payment_method="bank_transfer"))
    receipt_service.issue_receipt(db, business.id, d.id)
    assert calls["ctx_signed"] == [True] and calls["signed"] == [True]

def test_cash_is_not_signed(db, make_business, monkeypatch):
    calls = _setup(monkeypatch)
    business = Business.model_validate(make_business())
    d = receipt_service.create_draft(db, business, ReceiptDraftCreate(
        client_name="נועה", amount=100.0, description="שיעור", payment_method="cash"))
    receipt_service.issue_receipt(db, business.id, d.id)
    assert calls["ctx_signed"] == [False] and calls["signed"] == []

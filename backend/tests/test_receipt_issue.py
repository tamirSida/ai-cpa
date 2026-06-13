# backend/tests/test_receipt_issue.py
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi import HTTPException
from app.schemas.business import Business
from app.schemas.receipt import ReceiptDraftCreate
from app.services import receipt_service as rs

def _draft(db, biz, amount=100.0):
    return rs.create_draft(db, biz, ReceiptDraftCreate(client_name="נועה", amount=amount, description="עבודה", payment_method="bit"))

def test_issue_assigns_prefix_number_and_pdf(db, make_business, stub_receipt_assets):
    biz = Business.model_validate(make_business())  # receiptPrefix="2026", nextReceiptNumber=1
    issued = rs.issue_receipt(db, biz.id, _draft(db, biz, 2800).id)
    assert issued.receipt_number == "2026-0001" and issued.sequence_number == 1
    assert issued.status == "issued" and issued.issued_at is not None
    assert issued.pdf_url.endswith("receipts/%s/2026-0001.pdf" % biz.id) and issued.cloudinary_public_id

def test_issue_non_draft_409_and_pdf_retry(db, make_business, stub_receipt_assets):
    biz = Business.model_validate(make_business())
    issued = rs.issue_receipt(db, biz.id, _draft(db, biz).id)
    with pytest.raises(HTTPException) as e:  # double-issue of a receipt that already has a PDF
        rs.issue_receipt(db, biz.id, issued.id)
    assert e.value.status_code == 409 and e.value.detail["code"] == "receipt_not_draft"
    # retry path: issued receipt missing pdfUrl gets repaired without re-numbering
    rs._col(db, biz.id).document(issued.id).update({"pdfUrl": None, "cloudinaryPublicId": None})
    repaired = rs.issue_receipt(db, biz.id, issued.id)
    assert repaired.sequence_number == 1 and repaired.pdf_url

def test_concurrent_issue_assigns_unique_sequential_numbers(db, make_business, stub_receipt_assets):
    biz = Business.model_validate(make_business())
    drafts = [_draft(db, biz) for _ in range(10)]
    with ThreadPoolExecutor(max_workers=10) as ex:
        results = list(ex.map(lambda d: rs.issue_receipt(db, biz.id, d.id), drafts))
    assert sorted(r.sequence_number for r in results) == list(range(1, 11))  # no dupes, no gaps
    assert {r.receipt_number for r in results} == {f"2026-{n:04d}" for n in range(1, 11)}
    assert db.collection("businesses").document(biz.id).get().get("nextReceiptNumber") == 11
    events = list(db.collection("businesses").document(biz.id).collection("ledgerEvents")
                  .where(filter=rs.FieldFilter("type", "==", "receipt_issued")).stream())
    assert len(events) == 10


def test_issue_pdf_failure_still_issues(db, make_business, monkeypatch):
    # PDF/upload failure post-commit must NOT roll back issuance: the receipt is legally
    # issued (number + counter + ledger event committed), just without a pdfUrl.
    monkeypatch.setattr("app.services.receipt_service.render_pdf",
                        lambda name, ctx: (_ for _ in ()).throw(RuntimeError("render boom")))
    biz = Business.model_validate(make_business())
    issued = rs.issue_receipt(db, biz.id, _draft(db, biz).id)
    assert issued.receipt_number == "2026-0001" and issued.sequence_number == 1
    assert issued.status == "issued" and issued.pdf_url is None
    assert db.collection("businesses").document(biz.id).get().get("nextReceiptNumber") == 2
    events = list(db.collection("businesses").document(biz.id).collection("ledgerEvents")
                  .where(filter=rs.FieldFilter("type", "==", "receipt_issued")).stream())
    assert len(events) == 1

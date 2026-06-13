# עוסק פטור Receipt Compliance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring generated קבלה PDFs into §5/§18ב compliance — check details (gated to check payments), «מקור»/«מסמך ממוחשב»/«סה"כ שולם» labels, business bank details, payer-address warning, and a free self-signed מאובטחת digital signature applied only to traceable payment methods.

**Architecture:** Backend-first, TDD. New `signing_service` signs the WeasyPrint PDF with pyHanko + a self-signed PKCS#12 between render and Cloudinary upload, gated by payment method (cash/other render unsigned with a hand-sign note). Check details flow through the parser → chat follow-up → `checkDetails` on the receipt. Bank details live on the business profile.

**Tech Stack:** FastAPI + Pydantic v2 (`backend/.venv`, Python 3.12), Firestore emulator + pytest, WeasyPrint, **pyHanko** + `cryptography` (PKCS#12), Next.js 16 (dev on Node 22), Jinja2.

**Spec:** `docs/superpowers/specs/2026-06-13-osek-patur-receipt-compliance-design.md`

**Test command (backend):** `cd backend && FIRESTORE_EMULATOR_HOST=localhost:8080 GOOGLE_CLOUD_PROJECT=demo-tax-test .venv/bin/pytest <path> -q`
**Verify command (frontend):** `cd frontend && PATH="/opt/homebrew/opt/node@22/bin:$PATH" npx tsc --noEmit && PATH="/opt/homebrew/opt/node@22/bin:$PATH" npm run build`

---

## Task 1: CheckDetails schema + receipt fields

**Files:** Modify: `backend/app/schemas/receipt.py` · Test: `backend/tests/test_receipt_check_schema.py`

- [ ] **Step 1: Write the failing test**
```python
# backend/tests/test_receipt_check_schema.py
from app.schemas.receipt import CheckDetails, Receipt, ReceiptDraftCreate

def test_check_details_round_trips_camelcase():
    cd = CheckDetails(number="123", bank="לאומי", branch="800", due_date="2026-05-01")
    assert cd.model_dump(by_alias=True) == {"number": "123", "bank": "לאומי", "branch": "800", "dueDate": "2026-05-01"}

def test_draft_create_accepts_check_details():
    d = ReceiptDraftCreate(client_name="נועה", amount=100.0, description="שיעור",
                           payment_method="check",
                           check_details=CheckDetails(number="1", bank="b", branch="2", due_date="2026-05-01"))
    assert d.check_details.number == "1"

def test_draft_create_check_details_optional():
    d = ReceiptDraftCreate(client_name="נועה", amount=100.0, description="שיעור")
    assert d.check_details is None
```
- [ ] **Step 2: Run** `... pytest tests/test_receipt_check_schema.py -q` — expect ImportError (`CheckDetails` undefined).
- [ ] **Step 3: Implement** — in `backend/app/schemas/receipt.py`, add the model and the two fields:
```python
class CheckDetails(CamelModel):
    number: str
    bank: str
    branch: str
    due_date: str  # ISO YYYY-MM-DD; wire alias dueDate
```
Add `check_details: CheckDetails | None = None` to **both** `ReceiptDraftCreate` (after `payment_method`) and `Receipt` (after `description`).
- [ ] **Step 4: Run** `... pytest tests/test_receipt_check_schema.py -q` — expect 3 passed.
- [ ] **Step 5: Commit** `git add backend/app/schemas/receipt.py backend/tests/test_receipt_check_schema.py && git commit -m "feat(receipt): CheckDetails schema + check_details field"`

---

## Task 2: create_draft — gate + persist check details

**Files:** Modify: `backend/app/services/receipt_service.py:20-45` · Test: `backend/tests/test_receipt_check_service.py`

- [ ] **Step 1: Write the failing test**
```python
# backend/tests/test_receipt_check_service.py
import pytest
from fastapi import HTTPException
from app.schemas.receipt import CheckDetails, ReceiptDraftCreate
from app.services import receipt_service

def test_check_payment_requires_details(db, make_business):
    biz = make_business()
    from app.schemas.business import Business
    business = Business.model_validate(biz)
    with pytest.raises(HTTPException) as e:
        receipt_service.create_draft(db, business, ReceiptDraftCreate(
            client_name="נועה", amount=100.0, description="שיעור", payment_method="check"))
    assert e.value.status_code == 422 and e.value.detail["code"] == "missing_check_details"

def test_check_details_persisted(db, make_business):
    from app.schemas.business import Business
    business = Business.model_validate(make_business())
    r = receipt_service.create_draft(db, business, ReceiptDraftCreate(
        client_name="נועה", amount=100.0, description="שיעור", payment_method="check",
        check_details=CheckDetails(number="55", bank="דיסקונט", branch="125", due_date="2026-05-01")))
    assert r.check_details.number == "55" and r.check_details.bank == "דיסקונט"

def test_non_check_nulls_details(db, make_business):
    from app.schemas.business import Business
    business = Business.model_validate(make_business())
    r = receipt_service.create_draft(db, business, ReceiptDraftCreate(
        client_name="נועה", amount=100.0, description="שיעור", payment_method="bit",
        check_details=CheckDetails(number="55", bank="x", branch="1", due_date="2026-05-01")))
    assert r.check_details is None  # forced null for non-check
```
- [ ] **Step 2: Run** `... pytest tests/test_receipt_check_service.py -q` — expect failures (no gating; details not persisted/nulled).
- [ ] **Step 3: Implement** — in `create_draft`, after the client-snapshot block and before `ref = _col(...)`, add:
```python
    check = None
    if payload.payment_method == "check":
        cd = payload.check_details
        if cd is None or not all(s and s.strip() for s in (cd.number, cd.bank, cd.branch, cd.due_date)):
            api_error(422, "missing_check_details", "נדרשים פרטי המחאה: מספר, בנק, סניף ותאריך פירעון")
        check = cd
```
Then add to the `data` dict (after the `clientSnapshot` line):
```python
            "checkDetails": check.model_dump(by_alias=True) if check else None,
```
- [ ] **Step 4: Run** `... pytest tests/test_receipt_check_service.py -q` — expect 3 passed. Then `... pytest tests/test_receipt_service.py -q` (existing) — expect still green.
- [ ] **Step 5: Commit** `git add backend/app/services/receipt_service.py backend/tests/test_receipt_check_service.py && git commit -m "feat(receipt): gate + persist check details (required iff check)"`

---

## Task 3: Business bank details

**Files:** Modify: `backend/app/schemas/business.py`, `backend/app/services/business_service.py` · Test: `backend/tests/test_business_bank.py`

- [ ] **Step 1: Write the failing test**
```python
# backend/tests/test_business_bank.py
from app.schemas.business import BusinessCreate
from app.services import business_service

def test_create_persists_bank_fields(db):
    biz = business_service.create_business(db, "uid-bank", BusinessCreate(
        business_name="עסק", owner_name="תמיר", business_id_number="300123456", address="ת״א",
        bank_name="דיסקונט", bank_branch="125", bank_account="118863403"))
    assert biz.bank_name == "דיסקונט" and biz.bank_branch == "125" and biz.bank_account == "118863403"

def test_update_can_change_bank_account(db):
    from app.schemas.business import BusinessUpdate
    biz = business_service.create_business(db, "uid-bank2", BusinessCreate(
        business_name="עסק", owner_name="תמיר", business_id_number="300123456", address="ת״א"))
    out = business_service.update_business(db, biz.id, BusinessUpdate(bank_account="999"))
    assert out.bank_account == "999"
```
- [ ] **Step 2: Run** `... pytest tests/test_business_bank.py -q` — expect failure (unknown `bank_name`).
- [ ] **Step 3: Implement**
  - In `backend/app/schemas/business.py`, add to `BusinessCreate`, `BusinessUpdate`, and `Business` (all `Optional[str] = None`, max_length 60):
    `bank_name`, `bank_branch`, `bank_account`. For Create/Update use `Field(default=None, max_length=60)`.
  - In `backend/app/services/business_service.py`:
    - In `create_business`'s `data` dict add: `"bankName": payload.bank_name, "bankBranch": payload.bank_branch, "bankAccount": payload.bank_account,` (the existing `{k: v for k, v in data.items() if v is not None}` filter drops unset ones).
    - Add the three camel keys to `MUTABLE_FIELDS`: `"bankName", "bankBranch", "bankAccount"`.
- [ ] **Step 4: Run** `... pytest tests/test_business_bank.py tests/test_business_service.py tests/test_businesses_api.py -q` — expect all pass.
- [ ] **Step 5: Commit** `git add backend/app/schemas/business.py backend/app/services/business_service.py backend/tests/test_business_bank.py && git commit -m "feat(business): optional bank details on profile"`

---

## Task 4: Signing config + pyHanko dependency

**Files:** Modify: `backend/app/core/config.py`, `backend/requirements.txt`, `backend/.env.example`, `docker-compose.yml` · Test: `backend/tests/test_signing_config.py`

- [ ] **Step 1: Install the dependency**
Run: `cd backend && .venv/bin/pip install pyHanko && .venv/bin/pip show pyHanko | grep -i version`
Then add the resolved exact version to `backend/requirements.txt`, e.g. `pyHanko==<resolved>` (and `cryptography==<resolved>` if not already pinned — confirm with `.venv/bin/pip show cryptography`).
- [ ] **Step 2: Write the failing test**
```python
# backend/tests/test_signing_config.py
from app.core.config import get_settings

def test_signing_settings_default_unconfigured():
    get_settings.cache_clear()
    s = get_settings()
    assert s.receipt_signing_p12_path == "secrets/receipt-signing.p12"
    assert s.receipt_signing_p12_password == ""
```
- [ ] **Step 3: Run** `... pytest tests/test_signing_config.py -q` — expect AttributeError.
- [ ] **Step 4: Implement** — in `backend/app/core/config.py` `Settings`, after `cloudinary_url`:
```python
    receipt_signing_p12_path: str = "secrets/receipt-signing.p12"
    receipt_signing_p12_password: str = ""
```
In `backend/.env.example` add:
```
# Receipt digital signature (self-signed PKCS#12). Empty password => signing disabled (dev/CI).
RECEIPT_SIGNING_P12_PATH=secrets/receipt-signing.p12
RECEIPT_SIGNING_P12_PASSWORD=
```
`docker-compose.yml` already mounts `./backend/secrets:/code/secrets:ro`, so the `.p12` is available in-container — no compose change needed beyond confirming that mount exists.
- [ ] **Step 5: Run** `... pytest tests/test_signing_config.py -q` — expect 1 passed.
- [ ] **Step 6: Commit** `git add backend/app/core/config.py backend/requirements.txt backend/.env.example backend/tests/test_signing_config.py && git commit -m "feat(signing): config + pyHanko dependency"`

---

## Task 5: Self-signed certificate generator script

**Files:** Create: `backend/scripts/gen_signing_cert.py` · Test: `backend/tests/test_gen_signing_cert.py`

- [ ] **Step 1: Write the failing test**
```python
# backend/tests/test_gen_signing_cert.py
from cryptography.hazmat.primitives.serialization import pkcs12
from scripts.gen_signing_cert import build_p12

def test_build_p12_loads_back(tmp_path):
    data = build_p12("AI Bookkeeper Test", "pw123", years=5)
    key, cert, _ = pkcs12.load_key_and_certificates(data, b"pw123")
    assert key is not None and "AI Bookkeeper Test" in cert.subject.rfc4514_string()
```
- [ ] **Step 2: Run** `... pytest tests/test_gen_signing_cert.py -q` — expect ModuleNotFoundError.
- [ ] **Step 3: Implement** `backend/scripts/gen_signing_cert.py`:
```python
"""Generate a self-signed PKCS#12 for receipt signing (run once).
Usage: .venv/bin/python -m scripts.gen_signing_cert "AI Bookkeeper" <password> secrets/receipt-signing.p12
"""
import datetime
import sys
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID


def build_p12(common_name: str, password: str, years: int = 5) -> bytes:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name).issuer_name(name)
        .public_key(key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now).not_valid_after(now + datetime.timedelta(days=365 * years))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(digital_signature=True, content_commitment=True, key_encipherment=False,
                          data_encipherment=False, key_agreement=False, key_cert_sign=False,
                          crl_sign=False, encipher_only=False, decipher_only=False), critical=True)
        .sign(key, hashes.SHA256())
    )
    return pkcs12.serialize_key_and_certificates(
        b"receipt-signing", key, cert, None,
        serialization.BestAvailableEncryption(password.encode()))


if __name__ == "__main__":
    cn, password, out = sys.argv[1], sys.argv[2], sys.argv[3]
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_bytes(build_p12(cn, password))
    print(f"wrote {out}")
```
- [ ] **Step 4: Run** `... pytest tests/test_gen_signing_cert.py -q` — expect 1 passed.
- [ ] **Step 5: Commit** `git add backend/scripts/gen_signing_cert.py backend/tests/test_gen_signing_cert.py && git commit -m "feat(signing): self-signed PKCS#12 generator"`

---

## Task 6: signing_service

**Files:** Create: `backend/app/services/signing_service.py` · Test: `backend/tests/test_signing.py`

- [ ] **Step 1: Write the failing test**
```python
# backend/tests/test_signing.py
import io
from pyhanko.pdf_utils.reader import PdfFileReader
from scripts.gen_signing_cert import build_p12
from app.services import signing_service
from app.services.pdf_service import render_pdf
from app.core.config import get_settings

_CTX = {"business": {"businessName": "עסק", "ownerName": "תמיר", "businessIdNumber": "300123456"},
        "receipt": {"receiptNumber": "2026-0001", "issueDate": "2026-05-01", "amount": 100.0,
                    "paymentMethod": "bank_transfer", "description": "שיעור",
                    "clientSnapshot": {"name": "נועה"}}, "signed": True}

def test_is_signable_payment():
    assert signing_service.is_signable_payment("bank_transfer")
    assert signing_service.is_signable_payment("check")
    assert not signing_service.is_signable_payment("cash")
    assert not signing_service.is_signable_payment("other")

def test_unconfigured_is_false(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("RECEIPT_SIGNING_P12_PASSWORD", "")
    get_settings.cache_clear()
    assert signing_service.is_configured() is False

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
    r = PdfFileReader(io.BytesIO(signed))
    assert len(r.embedded_signatures) == 1                      # signature present (tamper-evident byte range)
    get_settings.cache_clear()
```
- [ ] **Step 2: Run** `... pytest tests/test_signing.py -q` — expect ModuleNotFoundError.
- [ ] **Step 3: Implement** `backend/app/services/signing_service.py`:
```python
import os
from io import BytesIO

from app.core.config import get_settings

# §18ב(ד): a מאובטחת-signed computerized document is limited to traceable payment methods.
# Bit/PayBox treated as transfer-equivalent (ITA practice); checks assumed crossed/non-negotiable.
SIGNABLE_METHODS = {"bank_transfer", "bit", "paybox", "credit_card", "check"}


def is_signable_payment(method: str) -> bool:
    return method in SIGNABLE_METHODS


def is_configured() -> bool:
    s = get_settings()
    return bool(s.receipt_signing_p12_password) and os.path.isfile(s.receipt_signing_p12_path)


def sign_pdf(pdf: bytes) -> bytes:
    """Apply an invisible PAdES signature with the configured self-signed PKCS#12.
    Raises if the cert can't be loaded — callers treat that as a PDF-attach failure."""
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
    from pyhanko.sign import signers

    s = get_settings()
    signer = signers.SimpleSigner.load_pkcs12(
        pfx_file=s.receipt_signing_p12_path, passphrase=s.receipt_signing_p12_password.encode())
    if signer is None:
        raise RuntimeError("receipt signing PKCS#12 failed to load")
    writer = IncrementalPdfFileWriter(BytesIO(pdf))
    out = signers.sign_pdf(
        writer, signers.PdfSignatureMetadata(field_name="Signature1", reason="קבלה ממוחשבת"),
        signer=signer)
    return out.getvalue()
```
- [ ] **Step 4: Run** `... pytest tests/test_signing.py -q` — expect 3 passed. *(If `load_pkcs12`/`sign_pdf` signatures differ in the installed pyHanko version, adjust per its API — the contract `sign_pdf(bytes)->bytes` and the tests stay.)*
- [ ] **Step 5: Commit** `git add backend/app/services/signing_service.py backend/tests/test_signing.py && git commit -m "feat(signing): pyHanko sign_pdf + payment eligibility"`

---

## Task 7: Wire signing into receipt issuance

**Files:** Modify: `backend/app/services/receipt_service.py:116-121` · Test: `backend/tests/test_receipt_signing_pipeline.py`

- [ ] **Step 1: Write the failing test** (stubs sign/upload; asserts the eligibility gate + `signed` flag)
```python
# backend/tests/test_receipt_signing_pipeline.py
from app.schemas.business import Business
from app.schemas.receipt import CheckDetails, ReceiptDraftCreate
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
```
- [ ] **Step 2: Run** `... pytest tests/test_receipt_signing_pipeline.py -q` — expect failure (`signing_service` not imported; no gating).
- [ ] **Step 3: Implement**
  - **Keep the suite hermetic:** at the top of `backend/tests/conftest.py` (module level, near `PROJECT_ID = "demo-tax-test"`) add `os.environ.setdefault("RECEIPT_SIGNING_P12_PASSWORD", "")`. Env vars take precedence over `.env`, so `signing_service.is_configured()` is False across the suite even when the developer has set a real password in `backend/.env` — existing issue tests never sign stub PDFs. The signing tests opt in via `monkeypatch.setenv(...)` + `get_settings.cache_clear()` (Task 6) or by patching `is_configured` (this task's pipeline test).
  - Add import at top of `receipt_service.py`: `from app.services import signing_service`.
  - Replace `_attach_pdf` body:
```python
def _attach_pdf(db, business_id: str, receipt_ref) -> None:
    rec = receipt_ref.get().to_dict()
    biz = db.collection("businesses").document(business_id).get().to_dict()
    will_sign = signing_service.is_configured() and signing_service.is_signable_payment(
        rec.get("paymentMethod", "unknown"))
    pdf = render_pdf("receipt.html", {"business": biz, "receipt": rec, "signed": will_sign})
    if will_sign:
        pdf = signing_service.sign_pdf(pdf)   # raises -> issue_receipt logs, repair branch re-runs
    up = upload_pdf(pdf, public_id=f"receipts/{business_id}/{rec['receiptNumber']}.pdf")
    receipt_ref.update({"pdfUrl": up.secure_url, "cloudinaryPublicId": up.public_id})
```
- [ ] **Step 4: Run** `... pytest tests/test_receipt_signing_pipeline.py tests/test_receipt_issue.py -q` — expect all pass (existing issue tests still green; in those, `is_configured()` is False so no signing).
- [ ] **Step 5: Commit** `git add backend/app/services/receipt_service.py backend/tests/test_receipt_signing_pipeline.py && git commit -m "feat(receipt): sign eligible PDFs, pass signed flag to template"`

---

## Task 8: Receipt PDF template — labels, payment block, totals, footer

**Files:** Modify: `backend/app/templates/receipt.html`, `backend/app/templates/base.html` · Test: `backend/tests/test_pdf_golden.py`

- [ ] **Step 1: Update the golden tests** (replace `backend/tests/test_pdf_golden.py` body, keeping the helper imports)
```python
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
```
- [ ] **Step 2: Run** `... pytest tests/test_pdf_golden.py -q` — expect failures (new labels/rows absent).
- [ ] **Step 3: Implement** — add to `base.html` `<style>` (before `</style>`): `.orig { font-size: 9pt; color: #666; margin-top: -3mm; }`. Replace `backend/app/templates/receipt.html` with:
```html
{% extends "base.html" %}
{% from "macros.html" import ltr %}
{% block content %}
<h1>קבלה {{ ltr(receipt.receiptNumber) }}</h1>
<p class="orig">מקור</p>
<p><strong>{{ business.businessName }}</strong><br>
{{ business.ownerName }} · עוסק פטור מס׳ {{ ltr(business.businessIdNumber) }}<br>
{% if business.address %}{{ business.address }}<br>{% endif %}
{% if business.phone %}{{ ltr(business.phone) }}{% endif %}{% if business.email %} · {{ ltr(business.email) }}{% endif %}</p>
<table class="fields">
<tr><td>תאריך הנפקה</td><td>{{ ltr(receipt.issueDate) }}</td></tr>
<tr><td>לקוח</td><td>{{ receipt.clientSnapshot.name }}{% if receipt.clientSnapshot.taxId %} ({{ ltr(receipt.clientSnapshot.taxId) }}){% endif %}
{% if receipt.clientSnapshot.address %}<br>{{ receipt.clientSnapshot.address }}{% endif %}</td></tr>
<tr><td>תיאור</td><td>{{ receipt.description }}</td></tr>
<tr><td>אמצעי תשלום</td><td>{{ payment_labels.get(receipt.paymentMethod, receipt.paymentMethod) }}</td></tr>
{% if receipt.paymentMethod == "check" and receipt.checkDetails %}
<tr><td>פרטי המחאה</td><td>מס׳ {{ ltr(receipt.checkDetails.number) }} · {{ receipt.checkDetails.bank }} · סניף {{ ltr(receipt.checkDetails.branch) }} · פירעון {{ ltr(receipt.checkDetails.dueDate) }}</td></tr>
{% elif receipt.paymentMethod == "bank_transfer" and business.bankAccount %}
<tr><td>חשבון לזיכוי</td><td>{{ business.bankName }} · סניף {{ ltr(business.bankBranch) }} · חשבון {{ ltr(business.bankAccount) }}</td></tr>
{% endif %}
<tr><td>סכום</td><td class="amount">{{ ltr(receipt.amount | ils) }}</td></tr>
<tr><td>סה״כ שולם</td><td class="amount">{{ ltr(receipt.amount | ils) }}</td></tr>
</table>
<p class="muted">עוסק פטור — אינו גובה מע״מ. מסמך זה מהווה קבלה בלבד ואינו חשבונית מס.<br>
{% if signed %}מסמך ממוחשב חתום דיגיטלית.{% else %}מסמך ממוחשב — נדרשת חתימה ידנית על העותק הנמסר.{% endif %}</p>
{% endblock %}
```
- [ ] **Step 4: Run** `... pytest tests/test_pdf_golden.py -q` — expect 5 passed.
- [ ] **Step 5: Commit** `git add backend/app/templates/receipt.html backend/app/templates/base.html backend/tests/test_pdf_golden.py && git commit -m "feat(receipt-pdf): מקור/מסמך-ממוחשב/סה״כ, payment block, bank, hand-sign note"`

---

## Task 9: Chat capture of check details

**Files:** Modify: `backend/app/schemas/ai_commands.py`, `backend/app/services/chat_service.py`, `backend/app/utils/hebrew.py` · Test: `backend/tests/integration/test_chat_check.py`

- [ ] **Step 1: Write the failing test**
```python
# backend/tests/integration/test_chat_check.py
from app.schemas.ai_commands import IntentType
from app.services.chat_service import compute_missing_fields
from app.utils.hebrew import build_followup_question

def test_check_payment_requires_check_fields():
    p = {"client_name": "נועה", "amount": 100.0, "description": "שיעור",
         "payment_received": True, "payment_method": "check"}
    missing = compute_missing_fields(IntentType.CREATE_RECEIPT, p)
    assert {"check_number", "check_bank", "check_branch", "check_due_date"} <= set(missing)

def test_non_check_no_check_fields():
    p = {"client_name": "נועה", "amount": 100.0, "description": "שיעור",
         "payment_received": True, "payment_method": "bit"}
    assert not any(f.startswith("check_") for f in compute_missing_fields(IntentType.CREATE_RECEIPT, p))

def test_followup_question_dedupes_check_fields():
    q = build_followup_question(IntentType.CREATE_RECEIPT, ["check_number", "check_bank", "check_branch", "check_due_date"])
    assert q.count("המחאה") == 1  # one combined question, not four
```
- [ ] **Step 2: Run** `... pytest tests/integration/test_chat_check.py -q` — expect failures.
- [ ] **Step 3: Implement**
  - `backend/app/schemas/ai_commands.py` `ReceiptPayload`: add four optional fields after `issue_receipt`:
    `check_number: Optional[str] = None`, `check_bank: Optional[str] = None`, `check_branch: Optional[str] = None`, `check_due_date: Optional[str] = None`.
  - `backend/app/services/chat_service.py` `compute_missing_fields`, inside the `CREATE_RECEIPT` branch (after the `payment_received` check) add:
```python
        if payload.get("payment_method") == "check":
            for f in ("check_number", "check_bank", "check_branch", "check_due_date"):
                if not payload.get(f):
                    missing.append(f)
```
  - `backend/app/utils/hebrew.py`: add the four keys to `_FIELD_Q`, all mapping to the same string, and dedupe in `build_followup_question`:
```python
    (IntentType.CREATE_RECEIPT, "check_number"): "מהם פרטי ההמחאה (מספר, בנק, סניף ותאריך פירעון)?",
    (IntentType.CREATE_RECEIPT, "check_bank"): "מהם פרטי ההמחאה (מספר, בנק, סניף ותאריך פירעון)?",
    (IntentType.CREATE_RECEIPT, "check_branch"): "מהם פרטי ההמחאה (מספר, בנק, סניף ותאריך פירעון)?",
    (IntentType.CREATE_RECEIPT, "check_due_date"): "מהם פרטי ההמחאה (מספר, בנק, סניף ותאריך פירעון)?",
```
Replace `build_followup_question`'s `qs` line with a de-duplicating version:
```python
def build_followup_question(intent: IntentType, missing_fields: list[str]) -> str:
    seen: set[str] = set()
    qs = []
    for f in missing_fields:
        q = _FIELD_Q.get((intent, f))
        if q and q not in seen:
            seen.add(q); qs.append(q)
    return " ".join(qs) or "חסרים לי כמה פרטים, אפשר לפרט?"
```
- [ ] **Step 4: Run** `... pytest tests/integration/test_chat_check.py tests/unit/test_hebrew.py -q` — expect pass.
- [ ] **Step 5: Commit** `git add backend/app/schemas/ai_commands.py backend/app/services/chat_service.py backend/app/utils/hebrew.py backend/tests/integration/test_chat_check.py && git commit -m "feat(chat): collect check details when payment is check"`

---

## Task 10: Executor maps check details into the draft

**Files:** Modify: `backend/app/services/chat_service.py:158-181` · Test: `backend/tests/integration/test_chat_check_execute.py`

- [ ] **Step 1: Write the failing test**
```python
# backend/tests/integration/test_chat_check_execute.py
from app.schemas.business import Business
from app.services import chat_service, receipt_service

def test_executor_persists_check_details(db, make_business):
    business = Business.model_validate(make_business())
    action_ref = db.collection("businesses").document(business.id).collection("pendingActions").document()
    action_ref.set({"id": action_ref.id})
    payload = {"client_name": "נועה", "amount": 500.0, "description": "שיעור", "payment_method": "check",
               "check_number": "55", "check_bank": "דיסקונט", "check_branch": "125", "check_due_date": "2026-07-01"}
    msg, result = chat_service._execute_receipt(db, business, payload, action_ref)
    r = receipt_service.get_receipt(db, business.id, result["receiptId"])
    assert r.check_details and r.check_details.number == "55" and r.check_details.due_date == "2026-07-01"
```
- [ ] **Step 2: Run** `... pytest tests/integration/test_chat_check_execute.py -q` — expect failure (details not mapped).
- [ ] **Step 3: Implement** — in `chat_service.py` add `CheckDetails` to the receipt-schema import (`from app.schemas.receipt import ReceiptDraftCreate, CheckDetails` — match existing import line), then in `_execute_receipt`'s `else` branch, build check details and pass them:
```python
        check_details = None
        if payload.get("payment_method") == "check":
            check_details = CheckDetails(
                number=payload.get("check_number"), bank=payload.get("check_bank"),
                branch=payload.get("check_branch"), due_date=payload.get("check_due_date"))
        draft = receipt_service.create_draft(db, business, ReceiptDraftCreate(
            client_id=client_id, client_name=name, amount=round_ils(payload["amount"]), currency="ILS",
            payment_method=payload.get("payment_method") or "unknown",
            description=payload["description"], check_details=check_details))
```
- [ ] **Step 4: Run** `... pytest tests/integration/test_chat_check_execute.py tests/integration/test_chat_confirm.py -q` — expect pass.
- [ ] **Step 5: Commit** `git add backend/app/services/chat_service.py backend/tests/integration/test_chat_check_execute.py && git commit -m "feat(chat): map check details into issued receipt"`

---

## Task 11: Precheck — payer-address compliance warning

**Files:** Modify: `backend/app/schemas/report.py`, `backend/app/services/report_service.py`, `backend/app/utils/hebrew.py` · Test: `backend/tests/test_report_payer_address.py`

- [ ] **Step 1: Write the failing test**
```python
# backend/tests/test_report_payer_address.py
from app.schemas.business import Business
from app.services import report_service
from tests.test_report_precheck import seed_receipt  # existing helper

def test_precheck_flags_receipt_without_payer_address(db, make_business):
    business = Business.model_validate(make_business())
    seed_receipt(db, business.id)  # seeds an issued receipt whose clientSnapshot has no address
    res = report_service.precheck(db, business, 2026)
    assert res.receipts_missing_payer_address  # non-empty
```
- [ ] **Step 2: Run** `... pytest tests/test_report_payer_address.py -q` — expect AttributeError.
- [ ] **Step 3: Implement**
  - `backend/app/schemas/report.py` `PrecheckResult`: add `receipts_missing_payer_address: list[str] = []`.
  - `backend/app/services/report_service.py` `precheck`: after the `missing_pdf`/`cancelled` lines add:
    `missing_payer_address = [r.receipt_number for r in receipts if r.status == "issued" and not (r.client_snapshot.address or "").strip()]`
    add `missing_payer_address` to the `lists` tuple used for `issues_count`, and pass
    `receipts_missing_payer_address=missing_payer_address` into the `PrecheckResult(...)`.
  - `backend/app/utils/hebrew.py` `render_precheck_summary`: after the `receipts_missing_pdf` block add:
```python
    if result.receipts_missing_payer_address:
        parts.append(f"{len(result.receipts_missing_payer_address)} קבלות ללא כתובת לקוח")
```
- [ ] **Step 4: Run** `... pytest tests/test_report_payer_address.py tests/test_report_precheck.py -q` — expect pass.
- [ ] **Step 5: Commit** `git add backend/app/schemas/report.py backend/app/services/report_service.py backend/app/utils/hebrew.py backend/tests/test_report_payer_address.py && git commit -m "feat(precheck): warn on receipts missing payer address"`

---

## Task 12: Frontend types

**Files:** Modify: `frontend/lib/types.ts`

- [ ] **Step 1: Implement** — in `frontend/lib/types.ts`:
  - `Business` interface: add `bankName?: string; bankBranch?: string; bankAccount?: string;`.
  - `Receipt` interface: add `checkDetails?: { number: string; bank: string; branch: string; dueDate: string };`.
  - `PrecheckResult` interface: add `receiptsMissingPayerAddress: string[];`.
- [ ] **Step 2: Verify** `cd frontend && PATH="/opt/homebrew/opt/node@22/bin:$PATH" npx tsc --noEmit` — expect zero errors.
- [ ] **Step 3: Commit** `git add frontend/lib/types.ts && git commit -m "feat(types): bank details, check details, payer-address precheck"`

---

## Task 13: Frontend — onboarding bank fields, annual-report check, receipt detail

**Files:** Modify: `frontend/app/onboarding/page.tsx`, `frontend/app/annual-report/page.tsx`, `frontend/components/ReceiptList.tsx` (receipt detail Sheet)

- [ ] **Step 1: Onboarding bank fields** — in `frontend/app/onboarding/page.tsx`:
  - Add to `FieldKey`: `"bankName" | "bankBranch" | "bankAccount"`.
  - Add to `FIELDS` (after `email`):
```ts
  { key: "bankName", label: "בנק (רשות)", type: "text", autoComplete: "off" },
  { key: "bankBranch", label: "סניף (רשות)", type: "text", inputMode: "numeric", ltr: true },
  { key: "bankAccount", label: "מספר חשבון (רשות)", type: "text", inputMode: "numeric", ltr: true },
```
  - `validateField`: add `case "bankName": case "bankBranch": case "bankAccount": return null;` (all optional).
  - Initial `form` state: add `bankName: "", bankBranch: "", bankAccount: ""`.
  - Edit-mode prefill `setForm({...})`: add `bankName: business.bankName ?? "", bankBranch: business.bankBranch ?? "", bankAccount: business.bankAccount ?? ""`.
  - Edit PATCH body and create POST body: include `bankName: form.bankName || null, bankBranch: form.bankBranch || null, bankAccount: form.bankAccount || null` (create already spreads `...form`, but send the `|| null` normalization like phone/email; for create add them explicitly alongside the spread).
  - Add the three camel keys to `BusinessUpdate` server-side acceptance — already done in Task 3 (`MUTABLE_FIELDS`), so the PATCH succeeds.
- [ ] **Step 2: Annual-report payer-address check** — in `frontend/app/annual-report/page.tsx`, add to `CHECKS` (and to `CheckKey`):
```ts
  { key: "receiptsMissingPayerAddress", label: "קבלות ללא כתובת לקוח", fixHref: "/receipts", fixLabel: "מעבר לקבלות" },
```
- [ ] **Step 3: Receipt detail** — in the receipt detail Sheet (`frontend/components/ReceiptList.tsx`), when `receipt.checkDetails` is present render a row: «פרטי המחאה: מס׳ {number} · {bank} סניף {branch} · פירעון {dueDate}» (LTR/`tnum` for number/branch/date). Follow the existing detail-row pattern in that file.
- [ ] **Step 4: Verify** `cd frontend && PATH="/opt/homebrew/opt/node@22/bin:$PATH" npx tsc --noEmit && PATH="/opt/homebrew/opt/node@22/bin:$PATH" npm run build` — expect zero errors, all routes built.
- [ ] **Step 5: Commit** `git add frontend/app/onboarding/page.tsx frontend/app/annual-report/page.tsx frontend/components/ReceiptList.tsx && git commit -m "feat(frontend): bank fields, payer-address check, check details in receipt detail"`

---

## Task 14: One-time signing cert (manual op) + full-suite verification

**Files:** none (ops) · No new tests

- [ ] **Step 1: Generate the dev/prod signing cert** (the user runs this; choose a strong password and put it in `backend/.env`):
```bash
cd backend
.venv/bin/python -m scripts.gen_signing_cert "AI Bookkeeper Receipts" "<password>" secrets/receipt-signing.p12
# then set RECEIPT_SIGNING_P12_PASSWORD=<password> in backend/.env
```
- [ ] **Step 2: Full backend suite** `cd backend && FIRESTORE_EMULATOR_HOST=localhost:8080 GOOGLE_CLOUD_PROJECT=demo-tax-test .venv/bin/pytest -q` — expect all green (186 prior + new; live tests still skipped).
- [ ] **Step 3: Frontend build** `cd frontend && PATH="/opt/homebrew/opt/node@22/bin:$PATH" npm run build` — expect success.
- [ ] **Step 4: Manual smoke** (optional, with the cert set + backend on real services): issue a receipt via chat with a bank-transfer payment → download the PDF → confirm «מקור», «מסמך ממוחשב חתום דיגיטלית», «סה"כ שולם», and the receiving-bank row; a cash receipt shows the hand-sign note and no «חתום דיגיטלית». Open the signed PDF in a viewer that shows signatures (e.g., Adobe) to confirm a signature is present (self-signed → "unknown signer," expected).
- [ ] **Step 5: Commit** any doc note updates to `docs/smoke-test.md` (add a "receipt signature" check) `git add docs/smoke-test.md && git commit -m "docs: receipt signature smoke step"`

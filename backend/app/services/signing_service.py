"""Receipt digital-signature service (invisible PAdES via pyHanko).

Signing is enabled only when a PKCS#12 bundle exists on disk AND a non-empty
password is configured; otherwise it is a no-op gate (dev/CI). The bundle is a
self-signed cert produced by scripts/gen_signing_cert.py.
"""

import os
from io import BytesIO

from app.core.config import get_settings

# Electronic / traceable payment methods that warrant a digitally signed receipt.
SIGNABLE_METHODS = {"bank_transfer", "bit", "paybox", "credit_card", "check"}


def is_signable_payment(method: str) -> bool:
    return method in SIGNABLE_METHODS


def is_configured() -> bool:
    s = get_settings()
    return bool(s.receipt_signing_p12_password) and os.path.isfile(s.receipt_signing_p12_path)


def sign_pdf(pdf: bytes) -> bytes:
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
    from pyhanko.sign import signers

    s = get_settings()
    signer = signers.SimpleSigner.load_pkcs12(
        pfx_file=s.receipt_signing_p12_path,
        passphrase=s.receipt_signing_p12_password.encode(),
    )
    if signer is None:
        raise RuntimeError("receipt signing PKCS#12 failed to load")
    writer = IncrementalPdfFileWriter(BytesIO(pdf))
    out = signers.sign_pdf(
        writer,
        signers.PdfSignatureMetadata(field_name="Signature1", reason="קבלה ממוחשבת"),
        signer=signer,
    )
    return out.getvalue()

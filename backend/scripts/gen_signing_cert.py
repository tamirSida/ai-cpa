"""Generate a self-signed PKCS#12 bundle for receipt signing.

Usage:
    python -m scripts.gen_signing_cert "<common_name>" "<password>" "<out_path>"

Produces a 2048-bit RSA self-signed certificate (not a CA) suitable for an
invisible PAdES signature on issued receipts. The bundle is encrypted with the
given password using cryptography's BestAvailableEncryption.
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import BestAvailableEncryption, pkcs12
from cryptography.x509.oid import NameOID


def build_p12(common_name: str, password: str, years: int = 5) -> bytes:
    """Build a self-signed PKCS#12 bundle and return its serialized bytes."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    not_before = datetime.now(timezone.utc)
    not_after = not_before + timedelta(days=365 * years)

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(not_before)
        .not_valid_after(not_after)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=True,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(key, hashes.SHA256())
    )

    return pkcs12.serialize_key_and_certificates(
        b"receipt-signing",
        key,
        cert,
        None,
        BestAvailableEncryption(password.encode()),
    )


if __name__ == "__main__":
    common_name, password, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    data = build_p12(common_name, password)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    print(f"wrote {len(data)} bytes to {out}")

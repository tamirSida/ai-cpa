from cryptography.hazmat.primitives.serialization import pkcs12

from scripts.gen_signing_cert import build_p12


def test_build_p12_loads_back(tmp_path):
    data = build_p12("AI Bookkeeper Test", "pw123", years=5)
    key, cert, _ = pkcs12.load_key_and_certificates(data, b"pw123")
    assert key is not None and "AI Bookkeeper Test" in cert.subject.rfc4514_string()

from app.core.config import get_settings


def test_signing_settings_default_unconfigured():
    get_settings.cache_clear()
    s = get_settings()
    assert s.receipt_signing_p12_path == "secrets/receipt-signing.p12"
    assert s.receipt_signing_p12_password == ""

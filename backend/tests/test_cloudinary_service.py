import cloudinary.uploader
import pytest
from fastapi import HTTPException

from app.services import cloudinary_service as cs

def _fake_upload(calls):
    def fake(data, **kw):
        calls.append(kw)
        return {"secure_url": f"https://res.cloudinary.com/demo/{kw.get('public_id', 'x')}", "public_id": kw.get("public_id", "expenses/b1/abc")}
    return fake

def test_upload_pdf_is_raw_with_pdf_extension(monkeypatch):
    monkeypatch.setattr(cs, "_ensure_config", lambda: None)  # config bootstrap tested separately
    calls = []
    monkeypatch.setattr(cloudinary.uploader, "upload", _fake_upload(calls))
    res = cs.upload_pdf(b"%PDF-", public_id="receipts/b1/2026-0001.pdf")
    assert calls[0]["resource_type"] == "raw" and calls[0]["public_id"].endswith(".pdf")
    assert res.public_id == "receipts/b1/2026-0001.pdf" and res.secure_url.startswith("https://")

def test_upload_image_uses_folder(monkeypatch):
    monkeypatch.setattr(cs, "_ensure_config", lambda: None)
    calls = []
    monkeypatch.setattr(cloudinary.uploader, "upload", _fake_upload(calls))
    cs.upload_image(b"\xff\xd8", folder="expenses/b1")
    assert calls[0]["resource_type"] == "image" and calls[0]["folder"] == "expenses/b1"

def test_ensure_config_raises_when_url_unset(monkeypatch):
    import cloudinary
    monkeypatch.setattr(cloudinary, "config", lambda: type("C", (), {"cloud_name": None})())
    monkeypatch.setattr(cs, "get_settings", lambda: type("S", (), {"cloudinary_url": ""})())
    with pytest.raises(HTTPException) as exc:
        cs._ensure_config()
    assert exc.value.status_code == 500 and exc.value.detail["code"] == "cloudinary_not_configured"

def test_fetch_asset_uses_client():
    class Resp:
        content = b"bytes"
        def raise_for_status(self): pass
    class Client:
        def get(self, url): assert url == "https://x/y.pdf"; return Resp()
    assert cs.fetch_asset("https://x/y.pdf", Client()) == b"bytes"

def test_fetch_asset_default_client_is_bounded(monkeypatch):
    import httpx
    captured = {}
    class Resp:
        content = b"pdfbytes"
        def raise_for_status(self): pass
    class FakeClient:
        def __init__(self, timeout=None): captured["timeout"] = timeout
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def get(self, url): captured["url"] = url; return Resp()
    monkeypatch.setattr(httpx, "Client", FakeClient)
    assert cs.fetch_asset("https://x/y.pdf") == b"pdfbytes"
    assert captured["timeout"] == cs.FETCH_TIMEOUT_SECONDS and captured["url"] == "https://x/y.pdf"

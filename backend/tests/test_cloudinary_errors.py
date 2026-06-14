import cloudinary.exceptions
import pytest
from fastapi import HTTPException

from app.services import cloudinary_service


@pytest.fixture(autouse=True)
def _skip_config(monkeypatch):
    monkeypatch.setattr(cloudinary_service, "_ensure_config", lambda: None)


def test_upload_image_rate_limited_maps_to_503(monkeypatch):
    def boom(*a, **k):
        raise cloudinary.exceptions.RateLimited("Slow Down, Out of Processing Capacity")
    monkeypatch.setattr("cloudinary.uploader.upload", boom)
    with pytest.raises(HTTPException) as e:
        cloudinary_service.upload_image(b"\xff\xd8\xff", folder="expenses/biz")
    assert e.value.status_code == 503 and e.value.detail["code"] == "cloudinary_busy"


def test_upload_pdf_generic_error_maps_to_502(monkeypatch):
    def boom(*a, **k):
        raise cloudinary.exceptions.Error("upstream boom")
    monkeypatch.setattr("cloudinary.uploader.upload", boom)
    with pytest.raises(HTTPException) as e:
        cloudinary_service.upload_pdf(b"%PDF-1.7", public_id="receipts/x.pdf")
    assert e.value.status_code == 502 and e.value.detail["code"] == "cloudinary_upload_failed"


def test_upload_image_success_still_returns_result(monkeypatch):
    monkeypatch.setattr("cloudinary.uploader.upload",
                        lambda *a, **k: {"secure_url": "https://x/i.jpg", "public_id": "expenses/biz/i"})
    res = cloudinary_service.upload_image(b"\xff\xd8\xff", folder="expenses/biz")
    assert res.secure_url == "https://x/i.jpg" and res.public_id == "expenses/biz/i"

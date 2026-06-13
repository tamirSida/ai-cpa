import io
import os
import cloudinary
import cloudinary.uploader
import httpx
from pydantic import BaseModel
from app.core.config import get_settings
from app.core.errors import api_error

# Bound every asset fetch so a slow/hung Cloudinary response can't stall report generation (Phase 6).
FETCH_TIMEOUT_SECONDS = 30.0

class UploadResult(BaseModel):
    secure_url: str
    public_id: str

def _ensure_config() -> None:
    if not cloudinary.config().cloud_name:  # SDK reads CLOUDINARY_URL env; force it from Settings
        url = get_settings().cloudinary_url
        if not url:
            # Fail loudly at upload time instead of letting the SDK misconfigure silently.
            api_error(500, "cloudinary_not_configured", "CLOUDINARY_URL is not set")
        os.environ["CLOUDINARY_URL"] = url
        cloudinary.reset_config()

def upload_pdf(data: bytes, public_id: str) -> UploadResult:
    _ensure_config()  # raw public_ids MUST keep the .pdf extension for correct delivery URLs
    res = cloudinary.uploader.upload(io.BytesIO(data), resource_type="raw", public_id=public_id, overwrite=False)
    return UploadResult(secure_url=res["secure_url"], public_id=res["public_id"])

def upload_image(data: bytes, folder: str) -> UploadResult:
    _ensure_config()  # HEIC lands fine as image; delivery uses f_jpg (Phase 4)
    res = cloudinary.uploader.upload(io.BytesIO(data), resource_type="image", folder=folder)
    return UploadResult(secure_url=res["secure_url"], public_id=res["public_id"])

def fetch_asset(url: str, client: httpx.Client | None = None) -> bytes:
    # Caller may pass a shared client (with its own timeout); otherwise use a bounded one-shot.
    if client is not None:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.content
    with httpx.Client(timeout=FETCH_TIMEOUT_SECONDS) as c:
        resp = c.get(url)
        resp.raise_for_status()
        return resp.content

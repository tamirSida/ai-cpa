import io
import os
import cloudinary
import cloudinary.uploader
from pydantic import BaseModel
from app.core.config import get_settings

class UploadResult(BaseModel):
    secure_url: str
    public_id: str

def _ensure_config() -> None:
    if not cloudinary.config().cloud_name:  # SDK reads CLOUDINARY_URL env; force it from Settings
        os.environ["CLOUDINARY_URL"] = get_settings().cloudinary_url
        cloudinary.reset_config()

def upload_pdf(data: bytes, public_id: str) -> UploadResult:
    _ensure_config()  # raw public_ids MUST keep the .pdf extension for correct delivery URLs
    res = cloudinary.uploader.upload(io.BytesIO(data), resource_type="raw", public_id=public_id, overwrite=False)
    return UploadResult(secure_url=res["secure_url"], public_id=res["public_id"])

def upload_image(data: bytes, folder: str) -> UploadResult:
    _ensure_config()  # HEIC lands fine as image; delivery uses f_jpg (Phase 4)
    res = cloudinary.uploader.upload(io.BytesIO(data), resource_type="image", folder=folder)
    return UploadResult(secure_url=res["secure_url"], public_id=res["public_id"])

def fetch_asset(url: str, client) -> bytes:
    resp = client.get(url)
    resp.raise_for_status()
    return resp.content

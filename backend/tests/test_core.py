import pytest
from fastapi import HTTPException

from app.core.errors import api_error


def test_api_error_shape():
    with pytest.raises(HTTPException) as exc:
        api_error(409, "business_exists", "User already has a business")
    assert exc.value.status_code == 409
    assert exc.value.detail == {"code": "business_exists", "message": "User already has a business"}


def test_get_db_emulator_roundtrip(db):
    ref = db.collection("smoke").document("x")
    ref.set({"ok": True})
    assert ref.get().to_dict() == {"ok": True}

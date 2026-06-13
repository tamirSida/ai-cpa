import pytest
from fastapi.testclient import TestClient

from app.core.firebase import get_db
from app.main import app

CREATE_BODY = {
    "businessName": "עיצובים של נועה", "ownerName": "נועה לוי",
    "businessIdNumber": "123456789", "address": "הרצל 1, תל אביב",
    "phone": "050-1234567", "email": "noa@example.com",
}


@pytest.fixture
def unauth_api(db):
    """TestClient with real auth dependency (no get_current_uid override)."""
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_db, None)


def test_create_business_201(api):
    r = api.post("/api/businesses", json=CREATE_BODY)
    assert r.status_code == 201
    body = r.json()
    assert body["ownerUserId"] == "test-uid"
    assert body["businessType"] == "osek_patur" and body["nextReceiptNumber"] == 1


def test_create_second_business_409(api):
    assert api.post("/api/businesses", json=CREATE_BODY).status_code == 201
    r = api.post("/api/businesses", json=CREATE_BODY)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "business_exists"


def test_me_404_then_200(api):
    r = api.get("/api/businesses/me")
    assert r.status_code == 404 and r.json()["detail"]["code"] == "business_not_found"
    api.post("/api/businesses", json=CREATE_BODY)
    r = api.get("/api/businesses/me")
    assert r.status_code == 200 and r.json()["businessName"] == "עיצובים של נועה"


def test_patch_mutable_field(api):
    biz_id = api.post("/api/businesses", json=CREATE_BODY).json()["id"]
    r = api.patch(f"/api/businesses/{biz_id}", json={"businessName": "סטודיו נועה"})
    assert r.status_code == 200 and r.json()["businessName"] == "סטודיו נועה"


def test_patch_immutable_field_422(api):
    biz_id = api.post("/api/businesses", json=CREATE_BODY).json()["id"]
    assert api.patch(f"/api/businesses/{biz_id}", json={"nextReceiptNumber": 999}).status_code == 422
    assert api.patch(f"/api/businesses/{biz_id}", json={"businessType": "osek_murshe"}).status_code == 422


def test_patch_foreign_business_403(api, make_business):
    other = make_business(ownerUserId="someone-else")
    r = api.patch(f"/api/businesses/{other['id']}", json={"businessName": "x"})
    assert r.status_code == 403 and r.json()["detail"]["code"] == "forbidden"


def test_missing_token_401(unauth_api):
    r = unauth_api.get("/api/businesses/me")
    assert r.status_code == 401 and r.json()["detail"]["code"] == "unauthenticated"


def test_garbage_token_401(unauth_api):
    r = unauth_api.get("/api/businesses/me", headers={"Authorization": "Bearer garbage"})
    assert r.status_code == 401 and r.json()["detail"]["code"] == "invalid_token"

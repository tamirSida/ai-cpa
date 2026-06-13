import pytest
from fastapi import HTTPException

from app.core.auth import get_current_uid, get_owned_business


def test_owned_business_ok(db, make_business):
    biz = make_business()
    result = get_owned_business(businessId=biz["id"], uid="test-uid", db=db)
    assert result.id == biz["id"] and result.owner_user_id == "test-uid"


def test_owned_business_404(db):
    with pytest.raises(HTTPException) as exc:
        get_owned_business(businessId="does-not-exist", uid="test-uid", db=db)
    assert exc.value.status_code == 404
    assert exc.value.detail["code"] == "business_not_found"


def test_owned_business_403(db, make_business):
    biz = make_business(ownerUserId="someone-else")
    with pytest.raises(HTTPException) as exc:
        get_owned_business(businessId=biz["id"], uid="test-uid", db=db)
    assert exc.value.status_code == 403
    assert exc.value.detail["code"] == "forbidden"


def test_get_current_uid_missing_credentials():
    with pytest.raises(HTTPException) as exc:
        get_current_uid(creds=None)
    assert exc.value.status_code == 401
    assert exc.value.detail["code"] == "unauthenticated"

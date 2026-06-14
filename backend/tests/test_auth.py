import pytest
from fastapi import HTTPException

from app.core.auth import (
    get_current_admin,
    get_current_uid,
    get_owned_business,
    require_active,
)
from app.schemas.user import User
from app.utils.dates import now_il


def _user(**overrides) -> User:
    now = now_il()
    base = dict(
        uid="u1",
        email="owner@example.com",
        status="active",
        role="user",
        created_at=now,
        updated_at=now,
    )
    base.update(overrides)
    return User(**base)


def test_owned_business_ok(db, make_business):
    biz = make_business()
    result = get_owned_business(businessId=biz["id"], user=_user(uid="test-uid"), db=db)
    assert result.id == biz["id"] and result.owner_user_id == "test-uid"


def test_owned_business_404(db):
    with pytest.raises(HTTPException) as exc:
        get_owned_business(businessId="does-not-exist", user=_user(uid="test-uid"), db=db)
    assert exc.value.status_code == 404
    assert exc.value.detail["code"] == "business_not_found"


def test_owned_business_403(db, make_business):
    biz = make_business(ownerUserId="someone-else")
    with pytest.raises(HTTPException) as exc:
        get_owned_business(businessId=biz["id"], user=_user(uid="test-uid"), db=db)
    assert exc.value.status_code == 403
    assert exc.value.detail["code"] == "forbidden"


def test_get_current_uid_missing_credentials():
    with pytest.raises(HTTPException) as exc:
        get_current_uid(creds=None)
    assert exc.value.status_code == 401
    assert exc.value.detail["code"] == "unauthenticated"


# --- require_active ---------------------------------------------------------

def test_require_active_pending_raises():
    with pytest.raises(HTTPException) as exc:
        require_active(user=_user(status="pending"))
    assert exc.value.status_code == 403
    assert exc.value.detail["code"] == "account_pending"


def test_require_active_disabled_raises():
    with pytest.raises(HTTPException) as exc:
        require_active(user=_user(status="disabled"))
    assert exc.value.status_code == 403
    assert exc.value.detail["code"] == "account_disabled"


def test_require_active_active_returns_user():
    user = _user(status="active")
    assert require_active(user=user) is user


# --- get_current_admin ------------------------------------------------------

def test_get_current_admin_non_admin_raises():
    with pytest.raises(HTTPException) as exc:
        get_current_admin(user=_user(status="active", role="user"))
    assert exc.value.status_code == 403
    assert exc.value.detail["code"] == "forbidden_not_admin"


def test_get_current_admin_admin_returns_user():
    user = _user(status="active", role="admin")
    assert get_current_admin(user=user) is user

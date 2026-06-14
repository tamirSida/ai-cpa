import pytest

from app.core import auth
from app.core.config import Settings


@pytest.fixture
def identity(api):
    """Override the token identity dep (the /users/me chain uses get_token_identity,
    NOT get_current_uid). Returns a setter so each test picks its uid/email/name."""
    def _set(uid="new-uid", email="new@x.com", name="New"):
        api.app.dependency_overrides[auth.get_token_identity] = (
            lambda: auth.TokenIdentity(uid=uid, email=email, name=name)
        )

    _set()  # sensible default
    yield _set
    api.app.dependency_overrides.pop(auth.get_token_identity, None)


def test_me_fresh_user_pending(api, identity, freeze_month):
    identity(uid="new-uid", email="new@x.com", name="New")
    resp = api.get("/api/users/me")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["uid"] == "new-uid"
    assert body["email"] == "new@x.com"
    assert body["status"] == "pending"
    assert body["role"] == "user"
    assert body["aiBudgetUsd"] is None
    assert body["usage"]["aiCostUsd"] == 0
    assert body["hasBusiness"] is False


def test_me_has_business_true_when_owned(api, identity, make_business, freeze_month):
    identity(uid="biz-owner", email="owner@x.com", name="Owner")
    make_business(ownerUserId="biz-owner")
    resp = api.get("/api/users/me")
    assert resp.status_code == 200, resp.text
    assert resp.json()["hasBusiness"] is True


def test_me_bootstrap_admin(api, identity, monkeypatch, freeze_month):
    monkeypatch.setattr(
        auth,
        "get_settings",
        lambda: Settings(
            _env_file=None,
            bootstrap_admin_emails=["boss@x.com"],
            default_ai_budget_usd=3.0,
        ),
    )
    identity(uid="boss-uid", email="boss@x.com", name="Boss")
    resp = api.get("/api/users/me")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["role"] == "admin"
    assert body["status"] == "active"
    assert body["aiBudgetUsd"] == 3.0


def test_me_idempotent_status_unchanged(api, identity, freeze_month):
    identity(uid="repeat-uid", email="repeat@x.com", name="Repeat")
    first = api.get("/api/users/me")
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "pending"
    second = api.get("/api/users/me")
    assert second.status_code == 200, second.text
    assert second.json()["status"] == "pending"

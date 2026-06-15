import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import HTTPException
from google.api_core.exceptions import Aborted

from app.core.config import Settings
from app.services import user_service
from app.utils.dates import now_il


def _settings(**overrides) -> Settings:
    # _env_file=None: hermetic, ignore developer .env.
    base = {"bootstrap_admin_emails": [], "default_ai_budget_usd": 3.0}
    base.update(overrides)
    return Settings(_env_file=None, **base)


def test_pending_default(db):
    user = user_service.ensure_user(
        db, uid="u1", email="alice@x.com", name="Alice", settings=_settings()
    )
    assert user.status == "pending"
    assert user.role == "user"
    assert user.ai_budget_usd is None
    assert user.display_name == "Alice"
    raw = db.collection("users").document("u1").get().to_dict()
    assert raw["status"] == "pending"
    assert "aiBudgetUsd" not in raw  # None dropped
    assert raw["displayName"] == "Alice"


def test_email_normalization(db):
    user = user_service.ensure_user(
        db, uid="u1", email="  New@X.COM ", name=None, settings=_settings()
    )
    assert user.email == "new@x.com"
    raw = db.collection("users").document("u1").get().to_dict()
    assert raw["email"] == "new@x.com"
    assert "displayName" not in raw  # None dropped


def test_bootstrap_admin(db):
    user = user_service.ensure_user(
        db, uid="u1", email="BOSS@x.com", name=None,
        settings=_settings(bootstrap_admin_emails=["boss@x.com"]),
    )
    assert user.role == "admin"
    assert user.status == "active"
    assert user.ai_budget_usd == 3.0
    raw = db.collection("users").document("u1").get().to_dict()
    assert raw["role"] == "admin" and raw["status"] == "active"
    assert raw["aiBudgetUsd"] == 3.0


def test_invite_accept(db):
    now = now_il()
    db.collection("invites").document("inv@x.com").set(
        {"status": "pending", "invitedByUid": "admin1", "createdAt": now, "updatedAt": now}
    )
    user = user_service.ensure_user(
        db, uid="u2", email="inv@x.com", name=None, settings=_settings()
    )
    assert user.status == "active"
    assert user.role == "user"
    assert user.invited_by_uid == "admin1"
    assert user.ai_budget_usd == 3.0
    invite = db.collection("invites").document("inv@x.com").get().to_dict()
    assert invite["status"] == "accepted"
    assert invite["acceptedByUid"] == "u2"


def test_revoked_invite_does_not_bypass(db):
    now = now_il()
    db.collection("invites").document("inv@x.com").set(
        {"status": "revoked", "invitedByUid": "admin1", "createdAt": now, "updatedAt": now}
    )
    user = user_service.ensure_user(
        db, uid="u2", email="inv@x.com", name=None, settings=_settings()
    )
    assert user.status == "pending"
    assert user.role == "user"
    assert user.ai_budget_usd is None


def test_email_required(db):
    with pytest.raises(HTTPException) as exc:
        user_service.ensure_user(db, uid="u1", email=None, name=None, settings=_settings())
    assert exc.value.status_code == 400
    assert exc.value.detail["code"] == "email_required"


def test_idempotency(db):
    first = user_service.ensure_user(
        db, uid="u1", email="alice@x.com", name="Alice", settings=_settings()
    )
    assert first.status == "pending"
    # Same uid, even with email now in bootstrap list -> existing doc returned as-is.
    second = user_service.ensure_user(
        db, uid="u1", email="alice@x.com", name="Alice",
        settings=_settings(bootstrap_admin_emails=["alice@x.com"]),
    )
    assert second.status == "pending"  # NOT promoted
    assert second.role == "user"
    assert second.created_at == first.created_at


def test_concurrent_first_signin_keeps_invited_active(db):
    """Race regression: on first sign-in the frontend fires /users/me and
    /businesses/me at once, so ensure_user can run concurrently for the same new
    uid. The invited user must end up ACTIVE — never overwritten to pending by the
    request that reads the invite as already consumed. Pre-transaction this could
    leave the user pending (and the invite accepted)."""
    now = now_il()
    db.collection("invites").document("race@x.com").set(
        {"status": "pending", "invitedByUid": "admin1", "createdAt": now, "updatedAt": now}
    )

    def call():
        # The Firestore EMULATOR uses pessimistic locking and raises Aborted "Transaction
        # lock timeout" (or, once max_attempts is spent, ValueError "Failed to commit
        # transaction in N attempts.") under heavy parallel contention on the same doc — a
        # load artifact that does NOT occur against real Firestore (optimistic concurrency).
        # Retry the whole call; ensure_user is idempotent, so once one thread creates the
        # active user the rest fast-path to it. A retry can't mask the bug under test: the
        # assertions below check the FINAL record is active (pre-transaction it could be
        # overwritten to pending regardless of retries).
        for attempt in range(15):
            try:
                return user_service.ensure_user(
                    db, uid="race-uid", email="race@x.com", name="R", settings=_settings()
                )
            except (Aborted, ValueError) as e:
                if isinstance(e, ValueError) and "Failed to commit transaction" not in str(e):
                    raise
                if attempt == 14:
                    raise
                time.sleep(0.2 * (attempt + 1))

    # 2 concurrent callers is the minimum that exposes the race (A creates active +
    # consumes the invite; B must not recreate it as pending) while keeping emulator
    # lock contention low so the test is reliable on slower CI runners.
    with ThreadPoolExecutor(max_workers=2) as ex:
        results = [f.result() for f in [ex.submit(call) for _ in range(2)]]

    # Every concurrent caller sees an active user — no pending overwrite.
    assert len(results) == 2
    assert all(u.status == "active" for u in results), [u.status for u in results]
    final = db.collection("users").document("race-uid").get().to_dict()
    assert final["status"] == "active"
    assert final.get("invitedByUid") == "admin1"
    # Invite consumed exactly once, atomically with the user creation.
    invite = db.collection("invites").document("race@x.com").get().to_dict()
    assert invite["status"] == "accepted"
    assert invite["acceptedByUid"] == "race-uid"

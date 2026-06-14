from dataclasses import dataclass

import pytest
from fastapi import HTTPException

from app.schemas.user import User
from app.utils.dates import now_il


@dataclass
class FakeUsage:
    input_tokens: int
    output_tokens: int


def _user(**overrides) -> User:
    now = now_il()
    base = dict(
        uid="u1",
        email="owner@example.com",
        status="active",
        ai_budget_usd=None,
        created_at=now,
        updated_at=now,
    )
    base.update(overrides)
    return User(**base)


# --- estimate_cost_micro ----------------------------------------------------

def test_estimate_cost_micro_exact():
    from app.core.config import get_settings
    from app.services.usage_service import estimate_cost_micro

    settings = get_settings()
    # 1000 * 0.40/1e6 + 500 * 1.60/1e6 = 0.0004 + 0.0008 = 0.0012 USD -> 1200 micro
    assert estimate_cost_micro(settings, "gpt-4.1-mini", FakeUsage(1000, 500)) == 1200


def test_estimate_cost_micro_unknown_model_falls_back_to_default():
    from app.core.config import get_settings
    from app.services.usage_service import estimate_cost_micro

    settings = get_settings()
    assert estimate_cost_micro(settings, "foo", FakeUsage(1000, 500)) == 1200


def test_estimate_cost_micro_none_usage_is_zero():
    from app.core.config import get_settings
    from app.services.usage_service import estimate_cost_micro

    settings = get_settings()
    assert estimate_cost_micro(settings, "gpt-4.1-mini", None) == 0


def test_estimate_cost_micro_zero_tokens_is_zero():
    from app.core.config import get_settings
    from app.services.usage_service import estimate_cost_micro

    settings = get_settings()
    assert estimate_cost_micro(settings, "gpt-4.1-mini", FakeUsage(0, 0)) == 0


def test_estimate_cost_micro_missing_tokens_is_zero():
    from app.core.config import get_settings
    from app.services.usage_service import estimate_cost_micro

    settings = get_settings()

    @dataclass
    class PartialUsage:
        input_tokens: int = None
        output_tokens: int = None

    assert estimate_cost_micro(settings, "gpt-4.1-mini", PartialUsage()) == 0


# --- record_cost / current_month_cost_micro ---------------------------------

def test_record_cost_accumulates(db, freeze_month):
    from app.services.usage_service import current_month_cost_micro, record_cost

    record_cost(db, "u1", "gpt-4.1-mini", FakeUsage(1000, 500))
    assert current_month_cost_micro(db, "u1") == 1200

    record_cost(db, "u1", "gpt-4.1-mini", FakeUsage(1000, 500))
    assert current_month_cost_micro(db, "u1") == 2400  # proves firestore.Increment


def test_record_cost_none_usage_is_noop(db, freeze_month):
    from app.services.usage_service import current_month_cost_micro, record_cost

    record_cost(db, "u1", "gpt-4.1-mini", None)
    assert current_month_cost_micro(db, "u1") == 0  # bucket never created


def test_current_month_cost_micro_absent_is_zero(db, freeze_month):
    from app.services.usage_service import current_month_cost_micro

    assert current_month_cost_micro(db, "nobody") == 0


# --- assert_budget ----------------------------------------------------------

def test_assert_budget_unlimited_never_raises(db, freeze_month):
    from app.services.usage_service import assert_budget, record_cost

    record_cost(db, "u1", "gpt-4.1-mini", FakeUsage(1000, 500))  # cost present
    assert_budget(db, _user(uid="u1", ai_budget_usd=None))  # no raise


def test_assert_budget_under_cap_passes(db, freeze_month):
    from app.services.usage_service import assert_budget, record_cost

    record_cost(db, "u1", "gpt-4.1-mini", FakeUsage(1000, 500))  # 0.0012 USD
    assert_budget(db, _user(uid="u1", ai_budget_usd=1.0))  # 0.0012 < 1.0


def test_assert_budget_over_cap_raises_429(db, freeze_month):
    from app.services.usage_service import assert_budget, record_cost

    record_cost(db, "u1", "gpt-4.1-mini", FakeUsage(1000, 500))  # 1200 micro
    with pytest.raises(HTTPException) as exc:
        assert_budget(db, _user(uid="u1", ai_budget_usd=0.001))  # cap 1000 micro < 1200
    assert exc.value.status_code == 429
    assert exc.value.detail["code"] == "ai_budget_exceeded"


def test_assert_budget_exactly_at_cap_raises(db, freeze_month):
    from app.services.usage_service import assert_budget, record_cost

    record_cost(db, "u1", "gpt-4.1-mini", FakeUsage(1000, 500))  # 1200 micro
    with pytest.raises(HTTPException) as exc:
        assert_budget(db, _user(uid="u1", ai_budget_usd=0.0012))  # cap == cost -> >= raises
    assert exc.value.status_code == 429


def test_assert_budget_nan_fails_closed(db, freeze_month):
    # Defense-in-depth: a bad stored value (NaN) must block, not silently pass.
    from app.services.usage_service import assert_budget

    with pytest.raises(HTTPException) as exc:
        assert_budget(db, _user(uid="u1", ai_budget_usd=float("nan")))
    assert exc.value.status_code == 429
    assert exc.value.detail["code"] == "ai_budget_exceeded"


def test_assert_budget_inf_fails_closed(db, freeze_month):
    from app.services.usage_service import assert_budget

    with pytest.raises(HTTPException) as exc:
        assert_budget(db, _user(uid="u1", ai_budget_usd=float("inf")))
    assert exc.value.status_code == 429


def test_assert_budget_negative_treated_as_zero_blocks(db, freeze_month):
    # A negative stored cap clamps to 0; any usage (even 0) is >= 0 -> blocks.
    from app.services.usage_service import assert_budget

    with pytest.raises(HTTPException) as exc:
        assert_budget(db, _user(uid="u1", ai_budget_usd=-5.0))
    assert exc.value.status_code == 429


# --- usage_summary ----------------------------------------------------------

def test_usage_summary_fresh_user(db, freeze_month):
    from app.services.usage_service import usage_summary

    summary = usage_summary(db, _user(uid="u1", ai_budget_usd=5.0))
    assert summary.month == "2026-06"
    assert summary.ai_cost_usd == 0.0
    assert summary.ai_budget_usd == 5.0
    assert summary.over_budget is False


def test_usage_summary_over_budget(db, freeze_month):
    from app.services.usage_service import record_cost, usage_summary

    record_cost(db, "u1", "gpt-4.1-mini", FakeUsage(1000, 500))  # 1200 micro -> 0.0012 USD
    summary = usage_summary(db, _user(uid="u1", ai_budget_usd=0.001))
    assert summary.ai_cost_usd == 1200 / 1_000_000
    assert summary.ai_budget_usd == 0.001
    assert summary.over_budget is True

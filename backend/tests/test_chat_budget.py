"""Chat-path AI dollar-budget hard block + cost recording.

Uses the HTTP layer (api fixture) so the router's user dependency wiring is
exercised end-to-end. The fast-path (confirm/cancel words) must stay FREE.
"""
from app.schemas.ai_commands import (IntentType, ParsedUserCommand, ParserFailure,
                                     ReceiptPayload)

FULL_RECEIPT = ParsedUserCommand(intent=IntentType.CREATE_RECEIPT, receipt=ReceiptPayload(
    client_name="נועה", amount=2800.0, description="עיצוב לוגו",
    payment_method="bit", payment_received=True))

USAGE_DOC = "users/test-uid/usage/2026-06"


def _usage_micro(db) -> int:
    snap = db.collection("users").document("test-uid").collection("usage").document("2026-06").get()
    return int(snap.to_dict().get("aiCostMicroUsd") or 0) if snap.exists else 0


def _seed_over_budget(db, _seed):
    """Re-seed test-uid with a tiny cap and an already-over-cap usage bucket."""
    _seed(db, uid="test-uid", email="owner@example.com", displayName="Owner",
          role="user", status="active", aiBudgetUsd=0.000001)
    db.collection("users").document("test-uid").collection("usage").document("2026-06") \
      .set({"month": "2026-06", "aiCostMicroUsd": 10})


def test_over_budget_hard_blocks_and_skips_llm(api, db, stub_parser, freeze_month, make_business):
    from tests.conftest import _seed_user
    _seed_over_budget(db, _seed_user)
    biz = make_business()
    stub_parser.queue_command(FULL_RECEIPT)  # would be popped only if the LLM were called

    resp = api.post(f"/api/businesses/{biz['id']}/chat/message", json={"text": "קיבלתי 2800 מנועה"})

    assert resp.status_code == 429
    assert resp.json()["detail"]["code"] == "ai_budget_exceeded"
    assert stub_parser.calls == []  # LLM was NOT called


def test_fast_path_confirm_stays_free_under_exhaustion(api, db, stub_parser, freeze_month, make_business):
    from tests.conftest import _seed_user
    biz = make_business()
    # 1) Drive one normal message while budget is Unlimited (default seed) to create a pending action.
    stub_parser.queue_command(FULL_RECEIPT)
    first = api.post(f"/api/businesses/{biz['id']}/chat/message", json={"text": "קיבלתי 2800 מנועה"})
    assert first.status_code == 200
    assert first.json()["action"]["status"] == "pending_confirmation"

    # 2) Now exhaust the budget.
    _seed_over_budget(db, _seed_user)

    # 3) Confirm with a CONFIRM word -> fast path, NO LLM, must NOT be budget-blocked.
    stub_parser.calls.clear()
    confirm = api.post(f"/api/businesses/{biz['id']}/chat/message", json={"text": "כן"})
    assert confirm.status_code != 429
    assert confirm.status_code == 200
    assert stub_parser.calls == []  # fast path never touched the LLM


def test_under_budget_records_cost(api, db, stub_parser, freeze_month, make_business):
    # Default seed: Unlimited budget.
    biz = make_business()
    stub_parser.queue_command(FULL_RECEIPT)

    resp = api.post(f"/api/businesses/{biz['id']}/chat/message", json={"text": "קיבלתי 2800 מנועה"})

    assert resp.status_code == 200
    assert _usage_micro(db) > 0  # FakeUsage(100,50) cost recorded


def test_parser_failure_not_charged(api, db, stub_parser, freeze_month, make_business):
    biz = make_business()
    stub_parser.usage = None
    stub_parser.queue_command(ParserFailure(reason="timeout"))

    resp = api.post(f"/api/businesses/{biz['id']}/chat/message", json={"text": "בלהבלה"})

    assert resp.status_code == 200  # fallback reply
    assert _usage_micro(db) == 0  # ParserFailure -> no cost recorded, bucket never created
